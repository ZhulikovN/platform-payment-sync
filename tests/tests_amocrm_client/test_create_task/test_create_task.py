# poetry run pytest tests/tests_amocrm_client/test_create_task/test_create_task.py -v -s --log-cli-level=INFO


import logging

import pytest

from app.core.amocrm_client import AmoCRMClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

TEST_LEAD_ID=39546093

logger = logging.getLogger(__name__)
@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_task_for_contact_manager() -> None:
    """Тест создания задачи для ответственного менеджера сделки."""
    logger.info("=" * 80)
    logger.info("ТЕСТ: Создание задачи для менеджера сделки")
    logger.info(f"Сделка ID: {TEST_LEAD_ID}")
    logger.info("=" * 80)

    client = AmoCRMClient()

    try:
        # Сначала получим информацию о сделке
        logger.info("\n1. Получение информации о сделке...")
        lead_response = await client._make_request("GET", f"/api/v4/leads/{TEST_LEAD_ID}")
        
        logger.info(f"  Название сделки: {lead_response.get('name')}")
        logger.info(f"  Ответственный ID: {lead_response.get('responsible_user_id')}")
        logger.info(f"  Воронка ID: {lead_response.get('pipeline_id')}")
        logger.info(f"  Статус ID: {lead_response.get('status_id')}")
        
        responsible_user_id = lead_response.get("responsible_user_id")
        if not responsible_user_id:
            raise AssertionError("У сделки нет ответственного менеджера")
        
        # Создаем задачу
        logger.info("\n2. Создание задачи для менеджера...")
        task_text = "Пришел платеж. Проверь все данные на корректность и отправь сделку в нужный этап"
        
        task_id = await client.create_task_for_contact_manager(
            lead_id=TEST_LEAD_ID,
            text=task_text,
        )
        
        logger.info(f"  ✓ Задача создана успешно!")
        logger.info(f"  Task ID: {task_id}")
        
        logger.info("\n3. Проверка созданной задачи...")
        task_response = await client._make_request("GET", f"/api/v4/tasks/{task_id}")
        
        logger.info(f"  Задача ID: {task_response['id']}")
        logger.info(f"  Текст: {task_response.get('text')}")
        logger.info(f"  Тип задачи: {task_response.get('task_type_id')}")
        logger.info(f"  Ответственный: {task_response.get('responsible_user_id')}")
        logger.info(f"  Привязана к сделке: {task_response.get('entity_id')}")
        logger.info(f"  Тип сущности: {task_response.get('entity_type')}")
        
        # Проверки
        assert task_response["id"] == task_id
        assert task_response["text"] == task_text
        assert task_response["responsible_user_id"] == responsible_user_id
        assert task_response["entity_id"] == TEST_LEAD_ID
        assert task_response["entity_type"] == "leads"
        assert task_response["task_type_id"] == 1
        
        logger.info("\n✓ Все проверки пройдены успешно!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\n✗ Ошибка в тесте: {e}", exc_info=True)
        raise
