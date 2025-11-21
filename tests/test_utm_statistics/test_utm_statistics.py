"""Тест для проверки записи UTM меток в кастомное поле сделки."""

import logging
import random

import pytest

from app.core.amocrm_client import AmoCRMClient
from app.core.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@pytest.mark.integration
def test_create_lead_with_utm_statistics() -> None:
    """
    Тест создания сделки с UTM метками в кастомном поле.
    """
    logger.info("=" * 80)
    logger.info("ТЕСТ: Создание сделки с UTM в кастомном поле")
    logger.info("=" * 80)

    client = AmoCRMClient()

    test_suffix = random.randint(100000, 999999)
    test_phone = f"+7999{test_suffix}"
    test_email = f"utm_test_{test_suffix}@example.com"
    test_name = f"UTM Тест {test_suffix}"

    logger.info(f"\nТестовые данные:")
    logger.info(f"  Имя: {test_name}")
    logger.info(f"  Телефон: {test_phone}")
    logger.info(f"  UTM source: amo_crm")

    try:
        logger.info(f"\n{'=' * 80}")
        logger.info("ШАГ 1: Создание контакта")
        logger.info(f"{'=' * 80}")

        contact_id = client.create_contact(
            name=test_name,
            phone=test_phone,
            email=test_email
        )

        logger.info(f"✅ Контакт создан: ID={contact_id}")

        logger.info(f"\n{'=' * 80}")
        logger.info("ШАГ 2: Создание сделки с UTM в кастомном поле")
        logger.info(f"{'=' * 80}")

        lead_id = client.create_lead_with_utm(
            name=f"Тестовая сделка UTM {test_suffix}",
            contact_id=contact_id,
            price=10000,
            utm_source="amo_crm"
        )

        logger.info(f"✅ Сделка создана: ID={lead_id}")

        logger.info(f"\n{'=' * 80}")
        logger.info("ШАГ 3: Проверка кастомного поля UTM")
        logger.info(f"{'=' * 80}")

        lead_response = client._make_request("GET", f"/api/v4/leads/{lead_id}")

        logger.info(f"\nСделка:")
        logger.info(f"  ID: {lead_response.get('id')}")
        logger.info(f"  Название: {lead_response.get('name')}")

        custom_fields = lead_response.get("custom_fields_values", [])
        utm_field = None
        
        for field in custom_fields:
            if field["field_id"] == 688736:
                utm_field = field
                break

        if utm_field:
            utm_value = utm_field["values"][0]["value"] if utm_field["values"] else None
            logger.info(f"\n✅ Поле 'utm_source S' найдено:")
            logger.info(f"   Значение: {utm_value}")
            assert utm_value == "amo_crm", f"Ожидали 'amo_crm', получили '{utm_value}'"
        else:
            logger.error(f"\n❌ Поле 'utm_source S' (ID: 810265) не найдено!")
            raise AssertionError("UTM поле не найдено в сделке")

        logger.info(f"\n✅ Тест завершен успешно!")
        logger.info("=" * 80)
        logger.info("ИТОГИ:")
        logger.info(f"  • Контакт создан: ID={contact_id}")
        logger.info(f"  • Сделка создана: ID={lead_id}")
        logger.info(f"  • UTM записан в кастомное поле: utm_source=amo_crm")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\n❌ Ошибка в тесте: {e}", exc_info=True)
        raise

