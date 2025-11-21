"""Тест для проверки записи UTM меток в tracking_data поля сделки."""

import logging

import pytest

from app.core.amocrm_client import AmoCRMClient
from app.core.settings import settings
from tests.test_config import TEST_CONTACT_ID

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@pytest.mark.integration
def test_create_lead_with_utm_tracking() -> None:
    """
    Тест создания сделки с UTM метками в tracking_data полях.
    
    Использует тестовый контакт ID={TEST_CONTACT_ID} и тестовую воронку.
    Проверяет все основные UTM параметры: source, medium, campaign, content, term, ym_uid.
    """
    logger.info("=" * 80)
    logger.info("ТЕСТ: Создание сделки с UTM в tracking_data полях")
    logger.info(f"Контакт: ID={TEST_CONTACT_ID}")
    logger.info(f"Воронка: ID={settings.AMO_PIPELINE_ID}")
    logger.info("=" * 80)

    client = AmoCRMClient()

    test_utm_data = {
        "utm_source": "vk_ads",
        "utm_medium": "cpc",
        "utm_campaign": "spring_2025",
        "utm_content": "banner_red",
        "utm_term": "ege_math",
        "ym_uid": "1234567890123456789"
    }

    logger.info(f"\nТестовые UTM данные:")
    for key, value in test_utm_data.items():
        logger.info(f"  {key}: {value}")

    try:
        logger.info(f"\n{'=' * 80}")
        logger.info("ШАГ 1: Создание сделки с полным набором UTM")
        logger.info(f"{'=' * 80}")

        lead_id = client.create_lead(
            name="Тестовая сделка с UTM tracking",
            contact_id=TEST_CONTACT_ID,
            price=15000,
            **test_utm_data
        )

        logger.info(f"Сделка создана: ID={lead_id}")
        assert lead_id > 0, "ID сделки должен быть положительным"

        logger.info(f"\n{'=' * 80}")
        logger.info("ШАГ 2: Проверка tracking_data полей")
        logger.info(f"{'=' * 80}")

        lead_response = client._make_request("GET", f"/api/v4/leads/{lead_id}")

        logger.info(f"\nСделка:")
        logger.info(f"  ID: {lead_response.get('id')}")
        logger.info(f"  Название: {lead_response.get('name')}")
        logger.info(f"  Воронка: {lead_response.get('pipeline_id')}")

        custom_fields = lead_response.get("custom_fields_values", [])
        
        utm_fields_map = {
            settings.AMO_LEAD_FIELD_UTM_SOURCE: ("utm_source", test_utm_data["utm_source"]),
            settings.AMO_LEAD_FIELD_UTM_MEDIUM: ("utm_medium", test_utm_data["utm_medium"]),
            settings.AMO_LEAD_FIELD_UTM_CAMPAIGN: ("utm_campaign", test_utm_data["utm_campaign"]),
            settings.AMO_LEAD_FIELD_UTM_CONTENT: ("utm_content", test_utm_data["utm_content"]),
            settings.AMO_LEAD_FIELD_UTM_TERM: ("utm_term", test_utm_data["utm_term"]),
            settings.AMO_LEAD_FIELD_YM_UID: ("_ym_uid", test_utm_data["ym_uid"]),
        }

        logger.info(f"\nПроверка полей:")
        found_fields = {}
        
        for field in custom_fields:
            field_id = field["field_id"]
            if field_id in utm_fields_map:
                field_name, expected_value = utm_fields_map[field_id]
                actual_value = field["values"][0]["value"] if field["values"] else None
                found_fields[field_name] = actual_value
                
                logger.info(f"{field_name} (ID: {field_id}): {actual_value}")
                assert actual_value == expected_value, f"Ожидали '{expected_value}', получили '{actual_value}'"

        for field_name, expected_value in [
            ("utm_source", test_utm_data["utm_source"]),
            ("utm_medium", test_utm_data["utm_medium"]),
            ("utm_campaign", test_utm_data["utm_campaign"]),
            ("utm_content", test_utm_data["utm_content"]),
            ("utm_term", test_utm_data["utm_term"]),
            ("_ym_uid", test_utm_data["ym_uid"]),
        ]:
            assert field_name in found_fields, f"Поле {field_name} не найдено в сделке"

        logger.info(f"\nТест завершен успешно!")
        logger.info("=" * 80)
        logger.info("ИТОГИ:")
        logger.info(f"  • Сделка создана: ID={lead_id}")
        logger.info(f"  • Контакт: ID={TEST_CONTACT_ID}")
        logger.info(f"  • Воронка: ID={settings.AMO_PIPELINE_ID}")
        logger.info(f"  • Все UTM параметры записаны в tracking_data поля:")
        for field_name, value in found_fields.items():
            logger.info(f"    - {field_name}: {value}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\nОшибка в тесте: {e}", exc_info=True)
        raise

