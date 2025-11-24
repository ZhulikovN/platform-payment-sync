"""Интеграционный тест для проверки метода create_lead из amocrm_client.py."""
#  poetry run pytest tests/amocrm_client/test_create_lead/test_create_lead.py -v -s --log-cli-level=INFO

import logging

import pytest

from app.core.amocrm_client import AmoCRMClient
from app.core.settings import settings
from tests.test_config import TEST_CONTACT_ID, TEST_CONTACT_NAME, TEST_CONTACT_PHONE, TEST_CONTACT_EMAIL, TEST_CONTACT_TG_ID, TEST_CONTACT_TG_USERNAME

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_lead_in_test_pipeline() -> None:
    """
    Тест создания сделки в тестовой воронке для единого тестового контакта.
    
    Проверяет корректность метода create_lead из amocrm_client.py:
    1. Создание сделки с базовыми параметрами
    2. Создание сделки в правильной тестовой воронке
    3. Обновление полей сделки
    4. Добавление примечания
    """
    logger.info("=" * 80)
    logger.info("ТЕСТ: Создание сделки (проверка create_lead)")
    logger.info(f"Тестовая воронка: AMO_PIPELINE_ID={settings.AMO_PIPELINE_ID}")
    logger.info(f"Тестовый контакт ID: {TEST_CONTACT_ID}")
    logger.info("=" * 80)

    client = AmoCRMClient()

    logger.info(f"\nШаг 1: Создание сделки в тестовой воронке")
    logger.info(f"   Pipeline ID: {settings.AMO_PIPELINE_ID}")
    logger.info(f"   Status ID: {settings.AMO_DEFAULT_STATUS_ID}")
    logger.info(f"   Контакт ID: {TEST_CONTACT_ID}")

    try:
        lead_id = await client.create_lead(
            name=f"Тестовая сделка для {TEST_CONTACT_NAME}",
            pipeline_id =10195498,
            status_id=80731486,
            contact_id=TEST_CONTACT_ID,
            price=0,
            utm_content="banner_red"
        )

        logger.info(f"\nСделка успешно создана!")
        logger.info(f"   ID сделки: {lead_id}")

        assert lead_id is not None, "ID сделки не должен быть None"
        assert isinstance(lead_id, int), "ID сделки должен быть целым числом"
        assert lead_id > 0, "ID сделки должен быть положительным числом"

        logger.info(f"\nШаг 2: Обновление бюджета сделки")
        test_price = 15000
        logger.info(f"   Бюджет: {test_price} руб")
        
        await client.update_lead(lead_id=lead_id, price=test_price)
        logger.info(f"Бюджет обновлен")

        logger.info(f"\nШаг 3: Обновление кастомных полей сделки")
        logger.info(f"   Направление курса: ЕГЭ (enum_id=1373609)")
        logger.info(f"   Предметы: Русский язык (1360286), Математика (1360288)")
        
        await client.update_lead_fields(
            lead_id=lead_id,
            subjects=[1360286, 1360288],
            direction=1373609,
        )
        logger.info(f"Кастомные поля обновлены")

        logger.info(f"\nШаг 4: Добавление примечания")
        note_text = f"""Тестовая запись
Имя клиента: {TEST_CONTACT_NAME}
Телефон: {TEST_CONTACT_PHONE}
Email: {TEST_CONTACT_EMAIL}
TGID: {TEST_CONTACT_TG_ID} | TG Username: {TEST_CONTACT_TG_USERNAME}
Источник: integration_test"""
        
        await client.add_lead_note(lead_id, note_text)
        logger.info(f"Примечание добавлено")

        logger.info(f"\nШаг 5: Проверка воронки и полей сделки")
        lead_response = await client._make_request("GET", f"/api/v4/leads/{lead_id}")
        
        actual_pipeline_id = lead_response.get("pipeline_id")
        actual_price = lead_response.get("price")
        
        logger.info(f"   Ожидаемая воронка: {settings.AMO_PIPELINE_ID}")
        logger.info(f"   Фактическая воронка: {actual_pipeline_id}")
        logger.info(f"   Бюджет: {actual_price} руб")
        
        assert actual_pipeline_id == settings.AMO_PIPELINE_ID, (
            f"Сделка должна быть в воронке {settings.AMO_PIPELINE_ID}, "
            f"но находится в {actual_pipeline_id}"
        )
        assert actual_price == test_price, f"Бюджет должен быть {test_price}, но равен {actual_price}"

        logger.info("\nВсе проверки пройдены успешно!")
        logger.info("=" * 80)
        logger.info("ИТОГИ:")
        logger.info(f"  • Контакт ID: {TEST_CONTACT_ID}")
        logger.info(f"  • Сделка создана: ID={lead_id}")
        logger.info(f"  • Воронка: {actual_pipeline_id} (тестовая)")
        logger.info(f"  • Бюджет: {actual_price} руб")
        logger.info(f"  • Направление: ЕГЭ")
        logger.info(f"  • Предметы: Русский язык, Математика")
        logger.info(f"  • Примечание: добавлено")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\nОшибка в тесте: {e}", exc_info=True)
        raise

