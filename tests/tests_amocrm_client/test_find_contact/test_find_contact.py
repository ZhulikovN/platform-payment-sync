"""Интеграционный тест для проверки методов поиска контактов."""
# poetry run pytest tests/tests_amocrm_client/test_find_contact/test_find_contact.py -v -s --log-cli-level=INFO

import logging

import pytest

from app.core.amocrm_client import AmoCRMClient
from tests.test_config import TEST_CONTACT_ID

NONEXISTENT_TG_ID = "777888999000"
NONEXISTENT_PHONE = "+7999909747"
NONEXISTENT_EMAIL = "test_909747@example.com"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_find_contact_by_custom_field() -> None:
    """Тест поиска контакта по кастомному полю (Telegram ID)."""
    logger.info("=" * 80)
    logger.info("ТЕСТ: Поиск контакта по кастомному полю (Telegram ID)")
    logger.info(f"Telegram ID для поиска: {NONEXISTENT_TG_ID}")
    logger.info("=" * 80)

    client = AmoCRMClient()

    try:
        contact = await client.find_contact_by_custom_field("777888999000")

        logger.info(f"\nРезультат поиска:")
        if contact:
            logger.info(f"  Контакт найден: ID={contact['id']}")
            logger.info(f"  Имя: {contact.get('name')}")
        else:
            logger.info(f"  Контакт не найден")
            raise AssertionError(f"Контакт с Telegram ID={NONEXISTENT_TG_ID} должен быть найден")

        logger.info("\nТест пройден успешно!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\nОшибка в тесте: {e}", exc_info=True)
        raise


@pytest.mark.integration
@pytest.mark.asyncio
async def test_find_contact_by_phone() -> None:
    """Тест поиска контакта по телефону."""
    logger.info("=" * 80)
    logger.info("ТЕСТ: Поиск контакта по телефону")
    logger.info(f"Телефон для поиска: {NONEXISTENT_PHONE}")
    logger.info("=" * 80)

    client = AmoCRMClient()

    try:
        contact = await client.find_contact_by_phone("7 (931) 537-17-33")

        logger.info(f"\nРезультат поиска:")
        if contact:
            logger.info(f"  Контакт найден: ID={contact['id']}")
            logger.info(f"  Имя: {contact.get('name')}")
        else:
            logger.info(f"  Контакт не найден")
            raise AssertionError(f"Контакт с телефоном={NONEXISTENT_PHONE} должен быть найден")

        logger.info("\nТест пройден успешно!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\nОшибка в тесте: {e}", exc_info=True)
        raise


@pytest.mark.integration
@pytest.mark.asyncio
async def test_find_contact_by_email() -> None:
    """Тест поиска контакта по email."""
    logger.info("=" * 80)
    logger.info("ТЕСТ: Поиск контакта по email")
    logger.info(f"Email для поиска: {NONEXISTENT_EMAIL}")
    logger.info("=" * 80)

    client = AmoCRMClient()

    try:
        contact = await client.find_contact_by_email(NONEXISTENT_EMAIL)

        logger.info(f"\nРезультат поиска:")
        if contact:
            logger.info(f"  Контакт найден: ID={contact['id']}")
            logger.info(f"  Имя: {contact.get('name')}")
        else:
            logger.info(f"  Контакт не найден")
            raise AssertionError(f"Контакт с email={NONEXISTENT_EMAIL} должен быть найден")

        logger.info("\nТест пройден успешно!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\nОшибка в тесте: {e}", exc_info=True)
        raise


@pytest.mark.integration
@pytest.mark.asyncio
async def test_find_contact_with_tg_id() -> None:
    """Тест общего метода поиска с приоритетом 1: Telegram ID."""
    logger.info("=" * 80)
    logger.info("ТЕСТ: Поиск контакта через find_contact (приоритет: Telegram ID)")
    logger.info(f"Telegram ID: {NONEXISTENT_TG_ID}")
    logger.info(f"Phone: {NONEXISTENT_PHONE}")
    logger.info(f"Email: {NONEXISTENT_EMAIL}")
    logger.info("=" * 80)

    client = AmoCRMClient()

    try:
        contact = await client.find_contact(
            tg_id=NONEXISTENT_TG_ID,
            phone=NONEXISTENT_PHONE,
            email=NONEXISTENT_EMAIL
        )

        logger.info(f"\nРезультат поиска:")
        if contact:
            logger.info(f"  Контакт найден: ID={contact['id']}")
            logger.info(f"  Имя: {contact.get('name')}")
            logger.info(f"  Найден по: Telegram ID (приоритет 1)")
        else:
            logger.info(f"  Контакт не найден")
            raise AssertionError("Контакт должен быть найден по Telegram ID")

        logger.info("\nТест пройден успешно!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\nОшибка в тесте: {e}", exc_info=True)
        raise


@pytest.mark.integration
@pytest.mark.asyncio
async def test_find_contact_with_phone_only() -> None:
    """Тест общего метода поиска с приоритетом 2: телефон."""
    logger.info("=" * 80)
    logger.info("ТЕСТ: Поиск контакта через find_contact (приоритет: телефон)")
    logger.info(f"Telegram ID: None")
    logger.info(f"Phone: {'+79632726457'}")
    logger.info(f"Email: {NONEXISTENT_EMAIL}")
    logger.info("=" * 80)

    client = AmoCRMClient()

    try:
        contact = await client.find_contact(
            tg_id=None,
            phone="+7999909747",
            email=NONEXISTENT_EMAIL
        )

        logger.info(f"\nРезультат поиска:")
        if contact:
            logger.info(f"  Контакт найден: ID={contact['id']}")
            logger.info(f"  Имя: {contact.get('name')}")
            logger.info(f"  Найден по: телефон (приоритет 2)")
        else:
            logger.info(f"  Контакт не найден")
            raise AssertionError("Контакт должен быть найден по телефону")

        logger.info("\nТест пройден успешно!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\nОшибка в тесте: {e}", exc_info=True)
        raise


@pytest.mark.integration
@pytest.mark.asyncio
async def test_find_contact_with_email_only() -> None:
    """Тест общего метода поиска с приоритетом 3: email."""
    logger.info("=" * 80)
    logger.info("ТЕСТ: Поиск контакта через find_contact (приоритет: email)")
    logger.info(f"Telegram ID: None")
    logger.info(f"Phone: None")
    logger.info(f"Email: {NONEXISTENT_EMAIL}")
    logger.info("=" * 80)

    client = AmoCRMClient()

    try:
        contact = await client.find_contact(
            tg_id=None,
            phone=None,
            email=NONEXISTENT_EMAIL
        )

        logger.info(f"\nРезультат поиска:")
        if contact:
            logger.info(f"  Контакт найден: ID={contact['id']}")
            logger.info(f"  Имя: {contact.get('name')}")
            logger.info(f"  Найден по: email (приоритет 3)")
        else:
            logger.info(f"  Контакт не найден")
            raise AssertionError("Контакт должен быть найден по email")

        logger.info("\nТест пройден успешно!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\nОшибка в тесте: {e}", exc_info=True)
        raise


@pytest.mark.integration
@pytest.mark.asyncio
async def test_find_active_lead() -> None:
    """Тест поиска активной сделки для контакта."""
    logger.info("=" * 80)
    logger.info("ТЕСТ: Поиск активной сделки для контакта")
    logger.info(f"Контакт ID: {TEST_CONTACT_ID}")
    logger.info("=" * 80)

    client = AmoCRMClient()

    try:
        lead = await client.find_active_lead(59634657, phone="79876726010")

        logger.info(f"\nРезультат поиска:")
        if lead:
            logger.info(f"  Активная сделка найдена: ID={lead['id']}")
            logger.info(f"  Название: {lead.get('name')}")
            logger.info(f"  Воронка: {lead.get('pipeline_id')}")
            logger.info(f"  Статус: {lead.get('status_id')}")
            logger.info(f"  Обновлена: {lead.get('updated_at')}")

            assert lead["id"] > 0, "ID сделки должен быть положительным"
            assert not lead.get("is_deleted", False), "Сделка не должна быть удаленной"
        else:
            logger.info(f"  Активная сделка не найдена")
            logger.info(f"  Это нормально, если у контакта нет активных сделок")

        logger.info("\nТест пройден успешно!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\nОшибка в тесте: {e}", exc_info=True)
        raise
