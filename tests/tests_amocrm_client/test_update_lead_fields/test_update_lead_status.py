"""Интеграционный тест для обновления этапа сделки через update_lead_fields."""
# pytest tests/amocrm_client/test_update_lead_fields/test_update_lead_status.py -v -s --log-cli-level=INFO

import logging

import pytest

from app.core.amocrm_client import AmoCRMClient
from app.core.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_lead_fields_with_subjects_and_status() -> None:
    """
    Тест обновления предметов И этапа одновременно.
    
    Проверяет что можно обновить и кастомные поля и status_id в одном вызове.
    """
    logger.info("=" * 80)
    logger.info("ТЕСТ: Обновление предметов + этап одновременно")
    logger.info("=" * 80)

    client = AmoCRMClient()
    
    test_lead_id = 39428477
    
    logger.info(f"\nИспользуем тестовую сделку: ID={test_lead_id}")
    
    try:
        lead_before = await client._make_request("GET", f"/api/v4/leads/{test_lead_id}")
        
        current_status = lead_before.get("status_id")
        
        logger.info(f"\nТекущий этап: {current_status}")
        
        new_subjects = [settings.AMO_SUBJECT_RUSSIAN, settings.AMO_SUBJECT_HISTORY]
        new_direction = settings.AMO_DIRECTION_EGE
        new_status = 80731242

        logger.info(f"\nОбновляем:")
        logger.info(f"  Предметы: Русский + История")
        logger.info(f"  Направление: ЕГЭ")
        logger.info(f"  Этап: {new_status}")
        
        # Обновить все поля
        await client.update_lead_fields(
            lead_id=test_lead_id,
            subjects=new_subjects,
            direction=new_direction,
            status_id=new_status,
        )
        
        logger.info(f"\nМетод update_lead_fields вызван")
        
        lead_after = await client._make_request("GET", f"/api/v4/leads/{test_lead_id}")
        
        updated_status = lead_after.get("status_id")
        
        logger.info(f"\nОбновленный этап: {updated_status}")
        
        updated_fields = lead_after.get("custom_fields_values", [])
        updated_subjects = None
        updated_direction = None
        
        for field in updated_fields:
            field_id = field.get("field_id")
            values = field.get("values", [])
            
            if field_id == settings.AMO_LEAD_FIELD_SUBJECTS:
                updated_subjects = [v.get("enum_id") for v in values]
            elif field_id == settings.AMO_LEAD_FIELD_DIRECTION:
                updated_direction = values[0].get("enum_id") if values else None
        
        logger.info(f"Обновленные предметы: {updated_subjects}")
        logger.info(f"Обновленное направление: {updated_direction}")
        
        assert updated_status == new_status, f"Этап должен быть {new_status}"
        assert updated_subjects is not None and set(updated_subjects) == set(new_subjects), "Предметы должны обновиться"
        assert updated_direction == new_direction, f"Направление должно быть {new_direction}"
        
        logger.info(f"\n✓ Все поля обновлены корректно!")
        logger.info(f"  • Предметы: {updated_subjects} ✓")
        logger.info(f"  • Направление: {updated_direction} ✓")
        logger.info(f"  • Этап: {current_status} → {updated_status} ✓")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\nОшибка в тесте: {e}", exc_info=True)
        raise

