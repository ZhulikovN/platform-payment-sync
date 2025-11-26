# poetry run pytest tests/tests_event_logger/test_event_logger.py -v
import pytest
from pathlib import Path
from datetime import datetime, timedelta

from app.db.event_logger import EventLogger


@pytest.fixture
async def temp_logger(tmp_path):
    """EventLogger с временной БД для тестов."""
    db_path = tmp_path / "test_payments.sqlite"
    logger = EventLogger(db_path=str(db_path))
    await logger._init_database()
    return logger


@pytest.mark.asyncio
async def test_init_database(temp_logger, tmp_path):
    """Тест инициализации БД."""
    db_path = Path(temp_logger.db_path)
    assert db_path.exists()
    assert db_path.stat().st_size > 0


@pytest.mark.asyncio
async def test_is_payment_processed_false(temp_logger):
    """Тест проверки несуществующего платежа."""
    exists = await temp_logger.is_payment_processed("nonexistent_payment")
    assert exists is False


@pytest.mark.asyncio
async def test_log_payment_success(temp_logger):
    """Тест логирования успешного платежа."""
    await temp_logger.log_payment(
        payment_id="test_payment_001",
        amount=10000,
        payment_date="2025-11-25 10:30:00",
        status="success",
        contact_id=12345,
        lead_id=67890,
        pipeline_id=4423755,
        status_id=63242022,
        is_lead_created=True,
        payload='{"test": "data"}',
    )

    exists = await temp_logger.is_payment_processed("test_payment_001")
    assert exists is True


@pytest.mark.asyncio
async def test_duplicate_payment(temp_logger):
    """Тест обнаружения дубликата."""
    await temp_logger.log_payment(
        payment_id="duplicate_test",
        amount=5000,
        payment_date="2025-11-25",
        status="success",
        payload="{}",
    )

    with pytest.raises(Exception):
        await temp_logger.log_payment(
            payment_id="duplicate_test",
            amount=5000,
            payment_date="2025-11-25",
            status="success",
            payload="{}",
        )


@pytest.mark.asyncio
async def test_get_payment_by_id(temp_logger):
    """Тест получения платежа по ID."""
    await temp_logger.log_payment(
        payment_id="get_test_123",
        amount=7500,
        payment_date="2025-11-25 12:00:00",
        status="success",
        contact_id=11111,
        lead_id=22222,
        pipeline_id=4423755,
        status_id=63242022,
        is_lead_created=False,
        payload='{"amount": 7500}',
    )

    payment = await temp_logger.get_payment_by_id("get_test_123")

    assert payment is not None
    assert payment["payment_id"] == "get_test_123"
    assert payment["amount"] == 7500
    assert payment["contact_id"] == 11111
    assert payment["lead_id"] == 22222
    assert payment["status"] == "success"
    assert payment["is_lead_created"] == 0


@pytest.mark.asyncio
async def test_get_payment_by_id_not_found(temp_logger):
    """Тест получения несуществующего платежа."""
    payment = await temp_logger.get_payment_by_id("nonexistent")
    assert payment is None


@pytest.mark.asyncio
async def test_log_payment_error(temp_logger):
    """Тест логирования ошибки обработки."""
    await temp_logger.log_payment(
        payment_id="error_test_456",
        amount=3000,
        payment_date="2025-11-25",
        status="error",
        error="Connection timeout",
        payload='{"error": true}',
    )

    payment = await temp_logger.get_payment_by_id("error_test_456")

    assert payment is not None
    assert payment["status"] == "error"
    assert payment["last_error"] == "Connection timeout"
    assert payment["contact_id"] is None
    assert payment["lead_id"] is None


@pytest.mark.asyncio
async def test_get_payments_for_date(temp_logger):
    """Тест получения всех платежей за дату."""
    import aiosqlite
    from datetime import UTC
    
    # Используем конкретную дату для теста
    test_date = "2025-11-25"
    test_timestamp = f"{test_date}T10:00:00Z"

    # Вставляем записи напрямую с нужным created_at
    async with aiosqlite.connect(temp_logger.db_path) as db:
        for i in range(1, 4):
            await db.execute(
                """
                INSERT INTO payment_events (
                    payment_id, amount, payment_date, status, payload, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (f"date_test_{i}", i * 1000, test_date, "success", "{}", test_timestamp),
            )
        await db.commit()

    payments = await temp_logger.get_payments_for_date(test_date)

    assert len(payments) == 3
    assert payments[0]["payment_id"] == "date_test_1"
    assert payments[1]["payment_id"] == "date_test_2"
    assert payments[2]["payment_id"] == "date_test_3"


@pytest.mark.asyncio
async def test_get_stats(temp_logger):
    """Тест получения статистики."""
    await temp_logger.log_payment(
        payment_id="stats_success_1",
        amount=5000,
        payment_date="2025-11-25",
        status="success",
        contact_id=1,
        lead_id=1,
        pipeline_id=4423755,
        is_lead_created=True,
        payload="{}",
    )

    await temp_logger.log_payment(
        payment_id="stats_success_2",
        amount=3000,
        payment_date="2025-11-25",
        status="success",
        contact_id=2,
        lead_id=2,
        pipeline_id=4423755,
        is_lead_created=False,
        payload="{}",
    )

    await temp_logger.log_payment(
        payment_id="stats_error",
        amount=1000,
        payment_date="2025-11-25",
        status="error",
        error="Test error",
        payload="{}",
    )

    stats = await temp_logger.get_stats()

    assert stats["by_status"]["success"] == 2
    assert stats["by_status"]["error"] == 1
    assert stats["by_pipeline"][4423755] == 2
    assert stats["lead_created_vs_found"]["created"] == 1
    assert stats["lead_created_vs_found"]["found"] == 1
    assert stats["total_amount"] == 8000
    assert stats["success_count"] == 2


@pytest.mark.asyncio
async def test_cleanup_old_records(temp_logger):
    """Тест удаления старых записей."""
    import aiosqlite

    async with aiosqlite.connect(temp_logger.db_path) as db:
        old_date = (datetime.now() - timedelta(days=40)).strftime("%Y-%m-%dT%H:%M:%SZ")

        await db.execute(
            """
            INSERT INTO payment_events (
                payment_id, amount, payment_date, status, payload, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("old_payment_1", 1000, "2025-10-01", "success", "{}", old_date),
        )

        await db.execute(
            """
            INSERT INTO payment_events (
                payment_id, amount, payment_date, status, payload, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("old_payment_2", 2000, "2025-10-02", "success", "{}", old_date),
        )

        await db.commit()

    await temp_logger.log_payment(
        payment_id="recent_payment",
        amount=5000,
        payment_date="2025-11-25",
        status="success",
        payload="{}",
    )

    deleted = await temp_logger.cleanup_old_records(days=30)

    assert deleted == 2

    recent = await temp_logger.get_payment_by_id("recent_payment")
    assert recent is not None

    old1 = await temp_logger.get_payment_by_id("old_payment_1")
    assert old1 is None

    old2 = await temp_logger.get_payment_by_id("old_payment_2")
    assert old2 is None


@pytest.mark.asyncio
async def test_is_lead_created_flag(temp_logger):
    """Тест флага is_lead_created."""
    await temp_logger.log_payment(
        payment_id="lead_created_test",
        amount=10000,
        payment_date="2025-11-25",
        status="success",
        lead_id=999,
        is_lead_created=True,
        payload="{}",
    )

    await temp_logger.log_payment(
        payment_id="lead_found_test",
        amount=5000,
        payment_date="2025-11-25",
        status="success",
        lead_id=888,
        is_lead_created=False,
        payload="{}",
    )

    payment_created = await temp_logger.get_payment_by_id("lead_created_test")
    payment_found = await temp_logger.get_payment_by_id("lead_found_test")

    assert payment_created["is_lead_created"] == 1
    assert payment_found["is_lead_created"] == 0


@pytest.mark.asyncio
async def test_multiple_pipelines_stats(temp_logger):
    """Тест статистики по нескольким воронкам."""
    await temp_logger.log_payment(
        payment_id="pipeline_site_1",
        amount=1000,
        payment_date="2025-11-25",
        status="success",
        pipeline_id=4423755,
        payload="{}",
    )

    await temp_logger.log_payment(
        payment_id="pipeline_site_2",
        amount=2000,
        payment_date="2025-11-25",
        status="success",
        pipeline_id=4423755,
        payload="{}",
    )

    await temp_logger.log_payment(
        payment_id="pipeline_yandex",
        amount=3000,
        payment_date="2025-11-25",
        status="success",
        pipeline_id=4423757,
        payload="{}",
    )

    stats = await temp_logger.get_stats()

    assert stats["by_pipeline"][4423755] == 2
    assert stats["by_pipeline"][4423757] == 1
    assert stats["total_amount"] == 6000

