# poetry run pytest tests/tests_amocrm_client/test_get_lead_by_id/test_get_lead_by_id.py -v -s --log-cli-level=INFO

import logging

import pytest

from app.core.amocrm_client import AmoCRMClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# ID существующей сделки для теста
TEST_LEAD_ID = 40095211


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_lead_by_id_existing() -> None:
    """Тест получения существующей сделки по ID."""
    logger.info("=" * 80)
    logger.info(f"ТЕСТ: Получение сделки по ID={TEST_LEAD_ID}")
    logger.info("=" * 80)

    client = AmoCRMClient()

    try:
        logger.info(f"\n1. Запрос сделки по ID: {TEST_LEAD_ID}")
        
        lead = await client.get_lead_by_id(TEST_LEAD_ID)

        logger.info(f"\n2. Результат:")
        if lead:
            logger.info(f"  ✓ Сделка найдена!")
            logger.info(f"  ID: {lead['id']}")
            logger.info(f"  Название: {lead.get('name')}")
            logger.info(f"  Воронка ID: {lead.get('pipeline_id')}")
            logger.info(f"  Статус ID: {lead.get('status_id')}")
            logger.info(f"  Бюджет: {lead.get('price')}")
            logger.info(f"  Ответственный ID: {lead.get('responsible_user_id')}")
            
            # Проверка контактов
            embedded_contacts = lead.get("_embedded", {}).get("contacts", [])
            logger.info(f"  Контакты: {len(embedded_contacts)}")
            if embedded_contacts:
                for idx, contact in enumerate(embedded_contacts, 1):
                    logger.info(f"    Контакт {idx}: ID={contact['id']}")
            
            # Проверки
            assert lead["id"] == TEST_LEAD_ID, f"ID сделки не совпадает: {lead['id']} != {TEST_LEAD_ID}"
            assert not lead.get("is_deleted", False), "Сделка удалена"
            assert len(embedded_contacts) > 0, "Нет привязанных контактов"
            
            logger.info(f"\n  ✓ Все проверки пройдены")
        else:
            logger.error(f"  ✗ Сделка {TEST_LEAD_ID} не найдена!")
            raise AssertionError(f"Lead {TEST_LEAD_ID} not found")

        logger.info("\n✓ Тест пройден успешно!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\n✗ Ошибка в тесте: {e}", exc_info=True)
        raise


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_lead_by_id_not_found() -> None:
    """Тест получения несуществующей сделки по ID."""
    logger.info("=" * 80)
    logger.info("ТЕСТ: Получение несуществующей сделки (ID=99999999)")
    logger.info("=" * 80)

    client = AmoCRMClient()
    non_existent_id = 00000

    try:
        logger.info(f"\n1. Запрос несуществующей сделки: {non_existent_id}")
        
        lead = await client.get_lead_by_id(non_existent_id)

        logger.info(f"\n2. Результат:")
        if lead is None:
            logger.info(f"  ✓ Сделка не найдена (ожидаемый результат)")
        else:
            logger.error(f"  ✗ Сделка неожиданно найдена: {lead['id']}")
            raise AssertionError(f"Lead {non_existent_id} should not exist")

        logger.info("\n✓ Тест пройден успешно!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\n✗ Ошибка в тесте: {e}", exc_info=True)
        raise
