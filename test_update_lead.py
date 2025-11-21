"""Упрощенный тест обновления сделки одним запросом (как в AmoCRM-GoogleSheets-Integration)."""

import logging

from app.core.amocrm_client import AmoCRMClient
from app.core.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def test_update_lead_simple() -> None:
    """Тест обновления сделки одним запросом."""
    # ID тестовой сделки
    test_lead_id = 39409809

    logger.info("=" * 80)
    logger.info("НАЧАЛО ТЕСТА: Обновление сделки (упрощенный вариант)")
    logger.info("=" * 80)

    try:
        # Создать клиент
        client = AmoCRMClient()

        # 1. Получить текущую сделку и контакт
        logger.info("\n1. Получение информации о сделке...")
        response = client._make_request("GET", f"/api/v4/leads/{test_lead_id}?with=contacts")
        logger.info(f"Сделка: {response.get('name')} (ID: {response.get('id')})")
        logger.info(f"Pipeline: {response.get('pipeline_id')}")
        logger.info(f"Status: {response.get('status_id')}")
        logger.info(f"Price: {response.get('price')}")

        # Получить ID контакта
        contact_id = None
        embedded = response.get("_embedded", {})
        contacts = embedded.get("contacts", [])
        if contacts:
            contact_id = contacts[0].get("id")
            logger.info(f"Контакт ID: {contact_id}")
        else:
            logger.warning("У сделки нет привязанного контакта!")

        # 2. Обновить контакт (имя, телефон, email, telegram username, telegram user id)
        if contact_id:
            logger.info("\n2. Обновление контакта...")
            contact_update = {
                "name": "Иванов Иван Иванович",
                "custom_fields_values": [
                    {
                        "field_code": "PHONE",
                        "values": [
                            {
                                "value": "+79991234567",
                                "enum_code": "WORK"
                            }
                        ]
                    },
                    {
                        "field_code": "EMAIL",
                        "values": [
                            {
                                "value": "ivanov@example.com",
                                "enum_code": "WORK"
                            }
                        ]
                    },
                    {
                        "field_id": settings.AMO_CONTACT_FIELD_TG_USERNAME,
                        "values": [{"value": "@ivanov_test"}]
                    },
                    {
                        "field_id": settings.AMO_CONTACT_FIELD_TG_ID,
                        "values": [{"value": "987654321"}]  # Telegram User ID
                    }
                ]
            }
            client._make_request("PATCH", f"/api/v4/contacts/{contact_id}", data=contact_update)
            logger.info("Контакт обновлен!")

        # 3. Обновить сделку одним запросом (название, бюджет, кастомные поля)
        logger.info("\n3. Обновление сделки...")

        # Подготовить кастомные поля
        custom_fields_values = []

        # Добавить предметы (мультисписок)
        # Русский: 1360286, История: 1360288, Математика (База матем): 1369170
        custom_fields_values.append({
            "field_id": settings.AMO_LEAD_FIELD_SUBJECTS,
            "values": [
                {"enum_id": 1360286},  # Русский
                {"enum_id": 1360288},  # История
                {"enum_id": 1369170},  # База матем
            ]
        })

        # Добавить счетчик покупок (select)
        # 2 покупки → enum_id: 1373535
        custom_fields_values.append({
            "field_id": settings.AMO_LEAD_FIELD_PURCHASE_COUNT,
            "values": [{"enum_id": 1373535}]  # 2
        })

        # Добавить направление курса (select)
        # Направление ЕГЭ → enum_id: 1373609
        custom_fields_values.append({
            "field_id": settings.AMO_LEAD_FIELD_DIRECTION,
            "values": [{"enum_id": 1373609}]  # Направление ЕГЭ
        })

        # Сформировать JSON для обновления
        update_data = {
            "name": "Тестовая сделка - Полное обновление",
            "price": 35000,
            "custom_fields_values": custom_fields_values
        }

        # Отправить запрос (БЕЗ массива для PATCH!)
        result = client._make_request("PATCH", f"/api/v4/leads/{test_lead_id}", data=update_data)
        logger.info("Сделка успешно обновлена!")

        # 4. Проверить обновленную сделку
        logger.info("\n4. Проверка обновленных полей сделки...")
        updated_response = client._make_request("GET", f"/api/v4/leads/{test_lead_id}")
        logger.info(f"Название: {updated_response.get('name')}")
        logger.info(f"Бюджет: {updated_response.get('price')}")

        updated_fields = updated_response.get("custom_fields_values") or []
        if updated_fields:
            logger.info("\nОбновленные кастомные поля:")
            for field in updated_fields:
                field_id = field.get("field_id")
                field_name = field.get("field_name", "Unknown")
                values = field.get("values", [])
                if len(values) > 1:
                    # Мультисписок
                    value = ", ".join([v.get("value", "") for v in values])
                else:
                    value = values[0].get("value") if values else None
                logger.info(f"  - {field_name} (ID: {field_id}): {value}")

        # 5. Проверить обновленный контакт
        if contact_id:
            logger.info("\n5. Проверка обновленного контакта...")
            contact_response = client._make_request("GET", f"/api/v4/contacts/{contact_id}")
            logger.info(f"Имя контакта: {contact_response.get('name')}")

            contact_fields = contact_response.get("custom_fields_values") or []
            for field in contact_fields:
                field_code = field.get("field_code", "")
                field_id = field.get("field_id")
                values = field.get("values", [])

                if field_code == "PHONE":
                    value = values[0].get("value") if values else None
                    logger.info(f"Телефон: {value}")
                elif field_code == "EMAIL":
                    value = values[0].get("value") if values else None
                    logger.info(f"Email: {value}")
                elif field_id == settings.AMO_CONTACT_FIELD_TG_USERNAME:
                    value = values[0].get("value") if values else None
                    logger.info(f"Telegram username: {value}")
                elif field_id == settings.AMO_CONTACT_FIELD_TG_ID:
                    value = values[0].get("value") if values else None
                    logger.info(f"Telegram user ID: {value}")

        # 6. Добавить примечание
        logger.info("\n6. Добавление примечания...")
        note_text = """Оплата проведена (ТЕСТ - упрощенный вариант)
Имя клиента: Иванов Иван
Дата/время: 2025-11-21 00:20:00
Сумма: 35000 руб
Предметы: Русский, История, База матем
Источник: platform"""

        client.add_lead_note(test_lead_id, note_text)
        logger.info("Примечание успешно добавлено!")

        logger.info("\n" + "=" * 80)
        logger.info("ТЕСТ ЗАВЕРШЕН УСПЕШНО")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\nОШИБКА ТЕСТА: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    test_update_lead_simple()

