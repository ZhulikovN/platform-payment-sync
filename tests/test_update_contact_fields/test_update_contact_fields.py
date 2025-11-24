"""Интеграционный тест для обновления telegram полей в контакте."""
# pytest tests/test_update_contact_fields/test_update_contact_fields.py -v -s --log-cli-level=INFO

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
def test_update_contact_fields() -> None:
    """
    Тест обновления telegram полей в контакте (идемпотентно).
    
    Проверяет:
    1. Получение текущих telegram полей в контакте
    2. Обновление пустых полей (tg_id, tg_username)
    3. Проверка идемпотентности (не перезаписывает существующие)
    """
    logger.info("=" * 80)
    logger.info("ТЕСТ: Обновление telegram полей в контакте")
    logger.info("=" * 80)

    client = AmoCRMClient()
    
    test_contact_id = 59601681
    
    logger.info(f"\nИспользуем существующий контакт: ID={test_contact_id}")
    
    try:
        # Шаг 1: Получить текущее состояние контакта
        logger.info(f"\n{'=' * 80}")
        logger.info("ШАГ 1: Получение текущего состояния контакта")
        logger.info(f"{'=' * 80}")
        
        contact_before = client._make_request("GET", f"/api/v4/contacts/{test_contact_id}")
        
        logger.info(f"\nТекущие данные контакта:")
        logger.info(f"  Имя: {contact_before.get('name')}")
        
        current_fields = contact_before.get("custom_fields_values", [])
        
        current_tg_id = None
        current_tg_username = None
        
        logger.info(f"\nТекущие telegram поля:")
        
        for field in current_fields:
            field_id = field.get("field_id")
            field_code = field.get("field_code")
            values = field.get("values", [])
            
            if field_code == "PHONE":
                logger.info(f"  Телефон: {values[0].get('value') if values else 'N/A'}")
            elif field_code == "EMAIL":
                logger.info(f"  Email: {values[0].get('value') if values else 'N/A'}")
            elif field_id == settings.AMO_CONTACT_FIELD_TG_ID:
                current_tg_id = values[0]["value"] if values else None
                logger.info(f"  Telegram ID: {current_tg_id or '(пусто)'}")
            elif field_id == settings.AMO_CONTACT_FIELD_TG_USERNAME:
                current_tg_username = values[0]["value"] if values else None
                logger.info(f"  Telegram Username: {current_tg_username or '(пусто)'}")

        # Шаг 2: Обновление telegram полей
        logger.info(f"\n{'=' * 80}")
        logger.info("ШАГ 2: Обновление telegram полей (только пустые)")
        logger.info(f"{'=' * 80}")
        
        new_tg_id = "777888999000"
        new_tg_username = "test_update_user"
        
        logger.info(f"\nНовые значения для обновления:")
        logger.info(f"  Telegram ID: {new_tg_id}")
        logger.info(f"  Telegram Username: {new_tg_username}")
        
        client.update_contact_fields(
            contact_id=test_contact_id,
            tg_id=new_tg_id,
            tg_username=new_tg_username,
        )
        
        logger.info(f"\nМетод update_contact_fields вызван")

        # Шаг 3: Проверка результата
        logger.info(f"\n{'=' * 80}")
        logger.info("ШАГ 3: Проверка обновленных полей")
        logger.info(f"{'=' * 80}")
        
        contact_after = client._make_request("GET", f"/api/v4/contacts/{test_contact_id}")
        
        updated_fields = contact_after.get("custom_fields_values", [])
        
        updated_tg_id = None
        updated_tg_username = None
        
        logger.info(f"\nОбновленные telegram поля:")
        
        for field in updated_fields:
            field_id = field.get("field_id")
            values = field.get("values", [])
            
            if field_id == settings.AMO_CONTACT_FIELD_TG_ID:
                updated_tg_id = values[0]["value"] if values else None
                logger.info(f"  Telegram ID: {updated_tg_id or '(пусто)'}")
            elif field_id == settings.AMO_CONTACT_FIELD_TG_USERNAME:
                updated_tg_username = values[0]["value"] if values else None
                logger.info(f"  Telegram Username: {updated_tg_username or '(пусто)'}")
        
        # Проверки логики обновления
        logger.info(f"\n{'=' * 80}")
        logger.info("ШАГ 4: Проверка логики обновления")
        logger.info(f"{'=' * 80}")
        
        # Проверка: если было пусто - должно обновиться
        if not current_tg_id:
            logger.info(f"\n✓ tg_id было пусто, ожидаем обновление: {updated_tg_id}")
            assert updated_tg_id == new_tg_id, f"tg_id должен быть {new_tg_id}"
        else:
            logger.info(f"\n✓ tg_id уже было заполнено ({current_tg_id}), не должно измениться")
            assert updated_tg_id == current_tg_id, f"tg_id не должен перезаписаться (было {current_tg_id})"
        
        if not current_tg_username:
            logger.info(f"✓ tg_username было пусто, ожидаем обновление: {updated_tg_username}")
            assert updated_tg_username == new_tg_username, f"tg_username должен быть {new_tg_username}"
        else:
            logger.info(f"✓ tg_username уже было заполнено ({current_tg_username}), не должно измениться")
            assert updated_tg_username == current_tg_username, f"tg_username не должен перезаписаться"

        # Шаг 5: Проверка идемпотентности (повторный вызов)
        logger.info(f"\n{'=' * 80}")
        logger.info("ШАГ 5: Проверка идемпотентности (повторный вызов)")
        logger.info(f"{'=' * 80}")
        
        different_tg_id = "111222333444"
        different_tg_username = "different_user"
        
        logger.info(f"\nВызываем update_contact_fields повторно с другими значениями:")
        logger.info(f"  Telegram ID: {different_tg_id} (пытаемся перезаписать)")
        logger.info(f"  Telegram Username: {different_tg_username} (пытаемся перезаписать)")
        
        client.update_contact_fields(
            contact_id=test_contact_id,
            tg_id=different_tg_id,
            tg_username=different_tg_username,
        )
        
        # Проверяем, что ничего не изменилось
        contact_final = client._make_request("GET", f"/api/v4/contacts/{test_contact_id}")
        final_fields = contact_final.get("custom_fields_values", [])
        
        final_tg_id = None
        final_tg_username = None
        
        for field in final_fields:
            field_id = field.get("field_id")
            values = field.get("values", [])
            
            if field_id == settings.AMO_CONTACT_FIELD_TG_ID:
                final_tg_id = values[0]["value"] if values else None
            elif field_id == settings.AMO_CONTACT_FIELD_TG_USERNAME:
                final_tg_username = values[0]["value"] if values else None
        
        logger.info(f"\nПроверка: значения НЕ должны измениться при повторном вызове")
        logger.info(f"  Telegram ID: {final_tg_id} (должно остаться {updated_tg_id})")
        logger.info(f"  Telegram Username: {final_tg_username} (должно остаться {updated_tg_username})")
        
        assert final_tg_id == updated_tg_id, "tg_id не должен перезаписаться при повторном вызове"
        assert final_tg_username == updated_tg_username, "tg_username не должен перезаписаться"

        logger.info(f"\n✓ Все проверки пройдены успешно!")
        logger.info("=" * 80)
        logger.info("ИТОГИ:")
        logger.info(f"\nКОНТАКТ: ID={test_contact_id}")
        logger.info(f"  • Telegram ID: {current_tg_id or '(было пусто)'} → {updated_tg_id}")
        logger.info(f"  • Telegram Username: {current_tg_username or '(было пусто)'} → {updated_tg_username}")
        logger.info(f"\n  • Метод идемпотентный: повторный вызов не перезаписал данные ✓")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\nОшибка в тесте: {e}", exc_info=True)
        raise
