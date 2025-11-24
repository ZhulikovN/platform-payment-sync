"""Сервис обработки оплат - центральная бизнес-логика."""

import logging
from dataclasses import dataclass
from datetime import datetime

from app.core.amocrm_client import AmoCRMClient
from app.core.amocrm_mappings import SUBJECTS_MAPPING, get_direction_enum_id
from app.core.settings import settings
from app.models.payment_webhook import PaymentWebhook

logger = logging.getLogger(__name__)


@dataclass
class ProcessResult:
    """Результат обработки оплаты."""

    status: str  # "success", "duplicate", "contact_not_found", "lead_not_found", "error", "skipped"
    contact_id: int | None = None
    lead_id: int | None = None
    message: str = ""
    error: str | None = None


class PaymentProcessor:
    """Процессор для обработки оплат с платформы."""

    def __init__(self, amocrm_client: AmoCRMClient | None = None) -> None:
        """
        Инициализация процессора.

        Args:
            amocrm_client: Клиент для работы с amoCRM API (опционально для тестов)
        """
        self.client = amocrm_client or AmoCRMClient()

    def process_payment(self, payment: PaymentWebhook) -> ProcessResult:
        """
        Обработать оплату с платформы.

        Шаги обработки:
        1. Проверка дубликата по payment_id
        2. Матчинг контакта (tg_id → phone → email)
        3. Создание контакта с UTM (если не найден и CREATE_IF_NOT_FOUND=True)
        4. Обновление полей контакта (tg_id, tg_username) - только пустые
        5. Матчинг активной сделки (во ВСЕХ воронках)
        6. Создание сделки в AMO_PIPELINE_ID (если не найдена и CREATE_IF_NOT_FOUND=True)
        7. Обновление полей сделки (суммы, статус, даты, IDs)
        8. Создание примечания в сделке

        Args:
            payment: Данные об оплате

        Returns:
            ProcessResult с результатом обработки
        """
        payment_id = payment.payment_id or "unknown"
        logger.info("=" * 80)
        logger.info(f"Начало обработки оплаты: payment_id={payment_id}")
        logger.info("=" * 80)

        try:
            # Шаг 1: Проверка дубликата по payment_id
            # TODO: Реализовать через EventLogger.is_payment_processed()
            # if self.is_payment_duplicate(payment_id):
            #     logger.warning(f"Payment {payment_id} already processed (duplicate)")
            #     return ProcessResult(
            #         status="duplicate",
            #         message=f"Payment {payment_id} already processed",
            #     )

            # Шаг 2: Матчинг контакта
            contact = self._find_or_create_contact(payment)
            if contact is None:
                logger.error("Contact not found and CREATE_IF_NOT_FOUND=False")
                return ProcessResult(
                    status="contact_not_found",
                    message="Contact not found and CREATE_IF_NOT_FOUND=False",
                )

            contact_id = contact["id"] if isinstance(contact, dict) else contact
            logger.info(f"✓ Contact resolved: ID={contact_id}")

            # Шаг 3: Обновление полей контакта (идемпотентно)
            self._update_contact_fields(contact_id, payment)

            # Шаг 4: Матчинг активной сделки
            lead = self._find_or_create_lead(contact_id, payment)
            if lead is None:
                logger.error("Lead not found and CREATE_IF_NOT_FOUND=False")
                return ProcessResult(
                    status="lead_not_found",
                    contact_id=contact_id,
                    message="Lead not found and CREATE_IF_NOT_FOUND=False",
                )

            lead_id = lead["id"] if isinstance(lead, dict) else lead
            logger.info(f"✓ Lead resolved: ID={lead_id}")

            # Шаг 5: Обновление полей сделки
            self._update_lead_fields(lead_id, payment)

            # Шаг 6: Создание примечания
            self._add_payment_note(lead_id, payment)

            logger.info(f"✓ Payment {payment_id} processed successfully")
            logger.info("=" * 80)

            return ProcessResult(
                status="success",
                contact_id=contact_id,
                lead_id=lead_id,
                message=f"Payment {payment_id} processed successfully",
            )

        except Exception as e:
            logger.error(f"Error processing payment {payment_id}: {e}", exc_info=True)
            return ProcessResult(
                status="error",
                message=f"Error processing payment: {str(e)}",
                error=str(e),
            )

    def _find_or_create_contact(self, payment: PaymentWebhook) -> dict | int | None:
        """
        Найти или создать контакт.

        Приоритеты поиска:
        1. По tg_id (если есть)
        2. По телефону
        3. По email

        Args:
            payment: Данные об оплате

        Returns:
            Данные контакта (dict) или ID контакта (int), или None если не найден
        """
        user = payment.course_order.user
        tg_id = user.telegram_id or None
        phone = user.phone or None
        email = user.email or None

        logger.info(f"Поиск контакта: tg_id={tg_id}, phone={phone}, email={email}")

        # Поиск контакта по приоритетам
        contact = self.client.find_contact(tg_id=tg_id, phone=phone, email=email)

        if contact:
            logger.info(f"✓ Контакт найден: ID={contact['id']}")
            return contact

        # Контакт не найден
        logger.warning("Контакт не найден")

        if not settings.CREATE_IF_NOT_FOUND:
            logger.warning("CREATE_IF_NOT_FOUND=False, контакт не будет создан")
            return None

        # Создать новый контакт с UTM
        logger.info("Создание нового контакта с UTM метками...")
        name = f"{user.first_name} {user.last_name}".strip() or "Клиент без имени"
        tg_username = user.telegram_tag or None

        contact_id = self.client.create_contact(
            name=name,
            phone=phone,
            email=email,
            tg_id=tg_id,
            tg_username=tg_username,
        )

        logger.info(f"✓ Контакт создан: ID={contact_id}")
        return contact_id

    def _update_contact_fields(self, contact_id: int, payment: PaymentWebhook) -> None:
        """
        Обновить поля контакта (идемпотентно - только пустые поля).

        Args:
            contact_id: ID контакта
            payment: Данные об оплате
        """
        user = payment.course_order.user
        tg_id = user.telegram_id or None
        tg_username = user.telegram_tag or None

        if not tg_id and not tg_username:
            logger.info("Нет данных Telegram для обновления контакта")
            return

        logger.info(f"Обновление полей контакта {contact_id}...")
        self.client.update_contact_fields(
            contact_id=contact_id,
            tg_id=tg_id,
            tg_username=tg_username,
        )

    def _find_or_create_lead(
        self, contact_id: int, payment: PaymentWebhook
    ) -> dict | int | None:
        """
        Найти или создать активную сделку для контакта.

        Поиск во ВСЕХ воронках, выбор последней обновленной активной сделки.

        Args:
            contact_id: ID контакта
            payment: Данные об оплате

        Returns:
            Данные сделки (dict) или ID сделки (int), или None если не найдена
        """
        user = payment.course_order.user
        telegram_id = str(user.telegram_id) if user.telegram_id else None
        phone = user.phone or None
        email = user.email or None

        logger.info(f"Поиск активной сделки для контакта {contact_id}...")

        # Поиск активной сделки (во всех воронках)
        lead = self.client.find_active_lead(
            contact_id=contact_id,
            telegram_id=telegram_id,
            phone=phone,
            email=email
        )

        if lead:
            logger.info(
                f"✓ Активная сделка найдена: ID={lead['id']}, Pipeline={lead.get('pipeline_id')}"
            )
            return lead

        # Сделка не найдена
        logger.warning("Активная сделка не найдена")

        if not settings.CREATE_IF_NOT_FOUND:
            logger.warning("CREATE_IF_NOT_FOUND=False, сделка не будет создана")
            return None

        # Создать новую сделку в целевой воронке с UTM
        logger.info(
            f"Создание новой сделки в воронке {settings.AMO_PIPELINE_ID} с UTM метками..."
        )

        # Название сделки
        user_name = (
            f"{user.first_name} {user.last_name}".strip() or "Клиент без имени"
        )
        # Получить первый предмет для названия
        first_subject = (
            payment.subjects_list[0] if payment.subjects_list else "Курс"
        )
        lead_name = f"Оплата {first_subject} - {user_name}"

        # Бюджет = сумма всех курсов в заказе (не amount!)
        price = sum(item.cost for item in payment.course_order.course_order_items)

        # UTM метки
        utm = payment.course_order.utm
        utm_source = utm.source or None
        utm_medium = utm.medium or None
        utm_campaign = utm.campaign or None
        utm_content = utm.content or None
        utm_term = utm.term or None
        ym_uid = utm.ym or None

        lead_id = self.client.create_lead(
            name=lead_name,
            contact_id=contact_id,
            price=price,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
            utm_term=utm_term,
            ym_uid=ym_uid,
        )

        logger.info(f"✓ Сделка создана: ID={lead_id}")
        return lead_id

    def _update_lead_fields(self, lead_id: int, payment: PaymentWebhook) -> None:
        """
        Обновить кастомные поля сделки.

        Обновляемые поля:
        - Предметы (из списка курсов)
        - Направление курса (ЕГЭ/ОГЭ)
        - Сумма последней оплаты (amount)
        - Общий оплаченный итог (инкрементально)
        - Статус оплаты
        - Дата/время последней оплаты
        - Invoice ID
        - Payment ID

        Args:
            lead_id: ID сделки
            payment: Данные об оплате
        """
        logger.info(f"Обновление полей сделки {lead_id}...")

        # Получить предметы из заказа
        subjects_enum_ids = []
        direction_enum_id = None

        for item in payment.course_order.course_order_items:
            subject_name = item.course.subject.name
            project_name = item.course.subject.project

            # Получить enum_id предмета
            subject_enum_id = SUBJECTS_MAPPING.get(subject_name)
            if subject_enum_id:
                subjects_enum_ids.append(subject_enum_id)
            else:
                logger.warning(f"Предмет '{subject_name}' не найден в маппинге")

            # Получить direction (ЕГЭ/ОГЭ) - берем из первого курса
            if direction_enum_id is None:
                direction_enum_id = get_direction_enum_id(project_name)

        # Удалить дубликаты предметов
        subjects_enum_ids = list(set(subjects_enum_ids))

        # Сумма оплаты - используем сумму всех курсов, а не amount из course_order
        # amount в course_order может быть флагом/процентом, а не реальной суммой
        amount = sum(item.cost for item in payment.course_order.course_order_items)

        # Статус оплаты
        payment_status = payment.course_order.status

        # Дата/время оплаты (ISO 8601)
        payment_date = payment.course_order.updated_at

        # Invoice ID и Payment ID
        invoice_id = payment.course_order.invoice_id
        payment_id = payment.course_order.payment_id

        # Обновить поля
        self.client.update_lead_fields(
            lead_id=lead_id,
            subjects=subjects_enum_ids if subjects_enum_ids else None,
            direction=direction_enum_id,
            last_payment_amount=amount,
            total_paid_increment=amount,  # Инкрементально добавить к общему итогу
            payment_status=payment_status,
            last_payment_date=payment_date,
            invoice_id=invoice_id,
            payment_id=payment_id,
        )

        logger.info(f"✓ Поля сделки {lead_id} обновлены")

    def _add_payment_note(self, lead_id: int, payment: PaymentWebhook) -> None:
        """
        Создать примечание в сделке с деталями оплаты.

        Шаблон примечания:
        ```
        Оплата проведена
        Имя клиента: {name}
        Дата/время: {datetime_local} / {datetime_utc}
        Статус: {status}
        Сумма: {amount} {currency}
        Метод: {payment_method}
        Курсы: {courses}
        Промокод: {promo_code}
        TGID: {tg_id} | TG Username: @{tg_username} | Телефон: {phone}
        Источник: {source}
        Invoice ID: {invoice_id}
        Payment ID: {payment_id}
        ```

        Args:
            lead_id: ID сделки
            payment: Данные об оплате
        """
        logger.info(f"Создание примечания в сделке {lead_id}...")

        user = payment.course_order.user
        order = payment.course_order
        utm = order.utm

        # Форматирование имени
        name = f"{user.first_name} {user.last_name}".strip() or "Не указано"

        # Форматирование даты/времени
        datetime_str = order.updated_at
        try:
            dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            datetime_utc = dt.isoformat() + "Z"
            # Конвертация в московское время (UTC+3)
            # TODO: Использовать pytz для корректной конвертации
            datetime_local = dt.strftime("%Y-%m-%d %H:%M:%S") + " (Moscow)"
        except Exception as e:
            logger.warning(f"Ошибка парсинга даты: {e}")
            datetime_local = datetime_str
            datetime_utc = datetime_str

        # Форматирование списка курсов
        courses_list = []
        for item in order.course_order_items:
            course_name = item.course.name
            subject_name = item.course.subject.name
            courses_list.append(f"{course_name} ({subject_name})")
        courses_str = "\n  ".join(courses_list)

        # Формирование текста примечания
        note_parts = [
            "Оплата проведена",
            "",
            f"Имя клиента: {name}",
            f"Дата/время: {datetime_local}",
            f"Дата/время UTC: {datetime_utc}",
            f"Статус: {order.status}",
            f"Сумма: {sum(item.cost for item in order.course_order_items)} {order.currency}",
        ]

        if order.payment_method:
            note_parts.append(f"Метод оплаты: {order.payment_method}")

        note_parts.append(f"Курсы:\n  {courses_str}")

        if order.code:
            note_parts.append(f"Промокод: {order.code}")

        # Telegram данные
        tg_parts = []
        if user.telegram_id:
            tg_parts.append(f"TGID: {user.telegram_id}")
        if user.telegram_tag:
            tg_parts.append(f"TG Username: @{user.telegram_tag}")
        if user.phone:
            tg_parts.append(f"Телефон: {user.phone}")
        if tg_parts:
            note_parts.append(" | ".join(tg_parts))

        if utm.source:
            note_parts.append(f"Источник: {utm.source}")

        if order.invoice_id:
            note_parts.append(f"Invoice ID: {order.invoice_id}")

        if order.payment_id:
            note_parts.append(f"Payment ID: {order.payment_id}")

        note_text = "\n".join(note_parts)

        # Добавить примечание
        self.client.add_lead_note(lead_id, note_text)

        logger.info(f"✓ Примечание добавлено в сделку {lead_id}")

