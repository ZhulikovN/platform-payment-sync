"""Интеграционный тест для создания контакта и сделки в тестовой воронке AmoCRM."""

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
def test_create_contact_and_lead_in_test_pipeline() -> None:
    """
    Тест создания контакта и сделки в тестовой воронке AMO_PIPELINE_ID=10195498.
    
    Проверяет правильную логику:
    1. Создать контакт
    2. НЕ вызывать find_active_lead() (контакт новый, сделок нет)
    3. Сразу создать сделку в тестовой воронке
    """
    logger.info("=" * 80)
    logger.info("ТЕСТ: Создание контакта и сделки в тестовой воронке")
    logger.info(f"Тестовая воронка: AMO_PIPELINE_ID={settings.AMO_PIPELINE_ID}")
    logger.info("=" * 80)

    client = AmoCRMClient()
    
    test_suffix = random.randint(100000, 999999)
    test_phone = f"+7999{test_suffix}"
    test_email = f"test_{test_suffix}@example.com"
    test_tg_id = f"999{test_suffix}"
    test_tg_username = f"@test_user_{test_suffix}"
    test_name = f"Тестовый Контакт {test_suffix}"

    logger.info(f"\nШаг 1: Создание тестового контакта")
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

        logger.info(f"\nКонтакт успешно создан!")
        logger.info(f"   ID контакта: {contact_id}")

        assert contact_id is not None, "ID контакта не должен быть None"
        assert isinstance(contact_id, int), "ID контакта должен быть целым числом"
        assert contact_id > 0, "ID контакта должен быть положительным числом"

        logger.info(f"\nШаг 2: Пропускаем find_active_lead()")
        logger.info(f"Правильная логика: контакт только что создан, сделок у него нет")
        logger.info(f"Вызов find_active_lead() был бы бесполезным API запросом")

        logger.info(f"\nШаг 3: Создание сделки в тестовой воронке")
        logger.info(f"   Pipeline ID: {settings.AMO_PIPELINE_ID}")
        logger.info(f"   Status ID: {settings.AMO_DEFAULT_STATUS_ID}")
        
        lead_id = client.create_lead(
            name=f"Тестовая сделка для {test_name}",
            contact_id=contact_id,
            price=0
        )

        logger.info(f"\nСделка успешно создана!")
        logger.info(f"   ID сделки: {lead_id}")

        assert lead_id is not None, "ID сделки не должен быть None"
        assert isinstance(lead_id, int), "ID сделки должен быть целым числом"
        assert lead_id > 0, "ID сделки должен быть положительным числом"

        logger.info(f"\nШаг 4: Обновление бюджета сделки")
        test_price = 15000
        logger.info(f"   Бюджет: {test_price} руб")
        
        client.update_lead(
            lead_id=lead_id,
            price=test_price
        )
        logger.info(f"Бюджет обновлен")

        logger.info(f"\nШаг 5: Обновление кастомных полей сделки")
        logger.info(f"   Направление курса: ЕГЭ (enum_id=1373609)")
        logger.info(f"   Предметы: Русский язык (1360286), Математика (1360288)")
        
        client.update_lead_fields(
            lead_id=lead_id,
            subjects=[1360286, 1360288],
            direction=1373609
        )
        logger.info(f"Кастомные поля обновлены")

        logger.info(f"\nШаг 6: Добавление примечания")
        note_text = f"""Тестовая запись
Имя клиента: {test_name}
Телефон: {test_phone}
Email: {test_email}
TGID: {test_tg_id} | TG Username: {test_tg_username}
Источник: integration_test"""
        
        client.add_lead_note(lead_id, note_text)
        logger.info(f"Примечание добавлено")

        logger.info(f"\nШаг 7: Проверка воронки и полей сделки")
        lead_response = client._make_request("GET", f"/api/v4/leads/{lead_id}")
        
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
        logger.info(f"  • Контакт создан: ID={contact_id}")
        logger.info(f"  • Сделка создана: ID={lead_id}")
        logger.info(f"  • Воронка: {actual_pipeline_id} (тестовая)")
        logger.info(f"  • Бюджет: {actual_price} руб")
        logger.info(f"  • Направление: ЕГЭ")
        logger.info(f"  • Предметы: Русский язык, Математика")
        logger.info(f"  • Примечание: добавлено")
        logger.info(f"  • Оптимизация: пропущен бесполезный вызов find_active_lead()")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\nОшибка в тесте: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    test_create_contact_and_lead_in_test_pipeline()
