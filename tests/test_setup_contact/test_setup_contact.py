"""Тест для создания тестового контакта."""

import logging
import random

import pytest

from app.core.amocrm_client import AmoCRMClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@pytest.mark.integration
def test_create_test_contact() -> None:
    """Создать тестовый контакт."""
    logger.info("=" * 80)
    logger.info("ТЕСТ: Создание тестового контакта")
    logger.info("=" * 80)

    client = AmoCRMClient()

    test_suffix = random.randint(100000, 999999)
    test_phone = f"+7999{test_suffix}"
    test_email = f"test_{test_suffix}@example.com"
    test_tg_id = f"999{test_suffix}"
    test_tg_username = f"test_user_{test_suffix}"
    test_name = f"Тестовый Контакт {test_suffix}"

    logger.info(f"\nТестовые данные:")
    logger.info(f"  Имя: {test_name}")
    logger.info(f"  Телефон: {test_phone}")
    logger.info(f"  Email: {test_email}")
    logger.info(f"  Telegram ID: {test_tg_id}")
    logger.info(f"  Telegram Username: {test_tg_username}")

    try:
        contact_id = client.create_contact(
            name=test_name,
            phone=test_phone,
            email=test_email,
            tg_id=test_tg_id,
            tg_username=test_tg_username
        )

        logger.info(f"\nКонтакт создан: ID={contact_id}")
        assert contact_id > 0

        logger.info("\n" + "=" * 80)
        logger.info("ИТОГИ:")
        logger.info(f"  • Контакт ID: {contact_id}")
        logger.info(f"  • Имя: {test_name}")
        logger.info(f"  • Телефон: {test_phone}")
        logger.info(f"  • Email: {test_email}")
        logger.info(f"  • Telegram ID: {test_tg_id}")
        logger.info(f"  • Telegram Username: {test_tg_username}")
        logger.info("\n⚠️  СКОПИРУЙТЕ ЭТИ ДАННЫЕ В tests/test_config.py:")
        logger.info(f'TEST_CONTACT_ID = {contact_id}')
        logger.info(f'TEST_CONTACT_PHONE = "{test_phone}"')
        logger.info(f'TEST_CONTACT_EMAIL = "{test_email}"')
        logger.info(f'TEST_CONTACT_TG_ID = "{test_tg_id}"')
        logger.info(f'TEST_CONTACT_TG_USERNAME = "{test_tg_username}"')
        logger.info(f'TEST_CONTACT_NAME = "{test_name}"')
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\n❌ Ошибка: {e}", exc_info=True)
        raise

