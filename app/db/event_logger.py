"""Event logger for payment processing events."""

import logging
import os
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)


class EventLogger:
    """
    Класс для логирования событий обработки платежей в SQLite.

    Защита от дубликатов и аналитика.
    """

    def __init__(self, db_path: str = "./db/payments.sqlite") -> None:
        """
        Инициализация EventLogger.

        Args:
            db_path: Путь к файлу базы данных SQLite
        """
        if not Path(db_path).is_absolute():
            base_path = Path(__file__).parent.parent.parent
            self.db_path = str(base_path / db_path)
        else:
            self.db_path = db_path

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    async def _init_database(self) -> None:
        """Инициализация базы данных и создание таблицы."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS payment_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,

                        -- Данные платежа
                        payment_id TEXT NOT NULL UNIQUE,
                        amount INTEGER NOT NULL,
                        payment_date TEXT NOT NULL,

                        -- Результат обработки
                        status TEXT NOT NULL,
                        contact_id INTEGER,
                        lead_id INTEGER,

                        -- Аналитика
                        pipeline_id INTEGER,
                        status_id INTEGER,
                        is_lead_created INTEGER,

                        -- Отладка
                        retry_count INTEGER DEFAULT 0,
                        last_error TEXT,
                        payload TEXT NOT NULL,

                        -- Временные метки
                        created_at TEXT NOT NULL,
                        processed_at TEXT
                    )
                """
                )

                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_payment_id
                    ON payment_events(payment_id)
                """
                )

                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_contact_id
                    ON payment_events(contact_id)
                """
                )

                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_lead_id
                    ON payment_events(lead_id)
                """
                )

                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_created_at
                    ON payment_events(created_at)
                """
                )

                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_status
                    ON payment_events(status)
                """
                )

                await db.commit()

            logger.info(f"База данных инициализирована: {self.db_path}")

        except Exception as e:
            logger.error(f"Ошибка при инициализации базы данных: {e}")
            raise

    async def is_payment_processed(self, payment_id: str) -> bool:
        """
        Проверка, был ли платеж уже обработан.

        Args:
            payment_id: ID платежа

        Returns:
            bool: True если платеж уже обрабатывался
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT COUNT(*) FROM payment_events WHERE payment_id = ?",
                    (payment_id,),
                ) as cursor:
                    row = await cursor.fetchone()
                    count = row[0] if row else 0

            exists = count > 0

            if exists:
                logger.warning(f"Платеж {payment_id} уже обработан (дубликат)")
            else:
                logger.debug(f"Платеж {payment_id} еще не обработан")

            return exists

        except Exception as e:
            logger.error(f"Ошибка при проверке дубликата: {e}")
            raise

    async def log_payment(
        self,
        payment_id: str,
        amount: int,
        payment_date: str,
        status: str,
        contact_id: int | None = None,
        lead_id: int | None = None,
        pipeline_id: int | None = None,
        status_id: int | None = None,
        is_lead_created: bool = False,
        error: str | None = None,
        payload: str = "",
    ) -> None:
        """
        Логирование события обработки платежа.

        Args:
            payment_id: ID платежа
            amount: Сумма платежа
            payment_date: Дата платежа
            status: Статус обработки (success, duplicate, error, skipped)
            contact_id: ID контакта в AmoCRM
            lead_id: ID сделки в AmoCRM
            pipeline_id: ID воронки
            status_id: ID этапа
            is_lead_created: Была ли создана новая сделка
            error: Текст ошибки (если есть)
            payload: Полный JSON webhook (для отладки)
        """
        timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        processed_at = timestamp if status == "success" else None

        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO payment_events (
                        payment_id, amount, payment_date, status,
                        contact_id, lead_id, pipeline_id, status_id,
                        is_lead_created, last_error, payload,
                        created_at, processed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payment_id,
                        amount,
                        payment_date,
                        status,
                        contact_id,
                        lead_id,
                        pipeline_id,
                        status_id,
                        1 if is_lead_created else 0,
                        error,
                        payload,
                        timestamp,
                        processed_at,
                    ),
                )

                await db.commit()

            logger.info(f"Платеж {payment_id} залогирован: " f"status={status}, contact={contact_id}, lead={lead_id}")

        except aiosqlite.IntegrityError as e:
            logger.warning(f"Попытка повторной записи платежа {payment_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Ошибка при логировании платежа: {e}")
            raise

    async def get_payment_by_id(self, payment_id: str) -> dict | None:
        """
        Получение информации о платеже по ID.

        Args:
            payment_id: ID платежа

        Returns:
            dict | None: Словарь с данными платежа или None
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row

                async with db.execute(
                    "SELECT * FROM payment_events WHERE payment_id = ? LIMIT 1",
                    (payment_id,),
                ) as cursor:
                    row = await cursor.fetchone()

                    if row:
                        return dict(row)
                    return None

        except Exception as e:
            logger.error(f"Ошибка при получении платежа: {e}")
            raise

    async def get_payments_for_date(self, date: str) -> list[dict]:
        """
        Получение всех платежей за указанную дату.

        Args:
            date: Дата в формате YYYY-MM-DD

        Returns:
            list[dict]: Список платежей
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row

                async with db.execute(
                    """
                    SELECT * FROM payment_events
                    WHERE date(created_at) = ?
                    ORDER BY created_at
                    """,
                    (date,),
                ) as cursor:
                    rows = await cursor.fetchall()

                    return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Ошибка при получении платежей за дату: {e}")
            raise

    async def get_stats(self) -> dict:
        """
        Получение статистики по всем платежам.

        Returns:
            dict: Статистика {total, success, error, duplicate, by_pipeline, etc}
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    """
                    SELECT status, COUNT(*) as count
                    FROM payment_events
                    GROUP BY status
                    """
                ) as cursor:
                    status_counts = {row[0]: row[1] async for row in cursor}

                async with db.execute(
                    """
                    SELECT pipeline_id, COUNT(*) as count
                    FROM payment_events
                    WHERE status = 'success' AND pipeline_id IS NOT NULL
                    GROUP BY pipeline_id
                    """
                ) as cursor:
                    pipeline_counts = {row[0]: row[1] async for row in cursor}

                async with db.execute(
                    """
                    SELECT is_lead_created, COUNT(*) as count
                    FROM payment_events
                    WHERE status = 'success'
                    GROUP BY is_lead_created
                    """
                ) as cursor:
                    lead_created_counts = {row[0]: row[1] async for row in cursor}

                async with db.execute(
                    """
                    SELECT SUM(amount) as total_amount, COUNT(*) as count
                    FROM payment_events
                    WHERE status = 'success'
                    """
                ) as cursor:
                    row = await cursor.fetchone()
                    total_amount = row[0] if row and row[0] else 0
                    success_count = row[1] if row and row[1] else 0

                return {
                    "by_status": status_counts,
                    "by_pipeline": pipeline_counts,
                    "lead_created_vs_found": {
                        "created": lead_created_counts.get(1, 0),
                        "found": lead_created_counts.get(0, 0),
                    },
                    "total_amount": total_amount,
                    "success_count": success_count,
                }

        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            raise

    async def cleanup_old_records(self, days: int = 30) -> int:
        """
        Удалить записи старше указанного количества дней.

        Args:
            days: Количество дней (по умолчанию 30)

        Returns:
            int: Количество удаленных записей

        Raises:
            Exception: При ошибках удаления
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    """
                    SELECT COUNT(*) FROM payment_events
                    WHERE datetime(created_at) < datetime('now', ? || ' days')
                    """,
                    (f"-{days}",),
                ) as cursor:
                    row = await cursor.fetchone()
                    count_before = row[0] if row else 0

                await db.execute(
                    """
                    DELETE FROM payment_events
                    WHERE datetime(created_at) < datetime('now', ? || ' days')
                    """,
                    (f"-{days}",),
                )

                await db.commit()

                logger.info(f"Удалено старых записей (старше {days} дней): {count_before}")
                return count_before

        except Exception as e:
            logger.error(f"Ошибка при очистке старых записей: {e}")
            raise
