"""Полный тест всех методов AmoCRMClient."""

import logging

from app.core.amocrm_client import AmoCRMClient
from app.core.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def test_amocrm_client_full() -> None:
    """Полный тест всех методов AmoCRMClient."""
    logger.info("=" * 80)
    logger.info("ПОЛНЫЙ ТЕСТ AmoCRMClient")
    logger.info("=" * 80)

    client = AmoCRMClient()
    test_contact_id = None
    test_lead_id = None
    
    try:
        # ==================== ЭТАП 1: Поиск существующего контакта ====================
        logger.info("\n" + "=" * 80)
        logger.info("ЭТАП 1: Поиск контакта")
        logger.info("=" * 80)
        
        # Попробуем найти контакт по телефону (уникальный для теста)
        import random
        test_suffix = random.randint(100000, 999999)
        test_phone = f"+7999{test_suffix}"
        test_email = f"test_{test_suffix}@example.com"
        test_tg_id = f"999{test_suffix}"
        
        logger.info(f"\n1.1. Поиск контакта по телефону: {test_phone}")
        contact = client.find_contact(tg_id=None, phone=test_phone, email=None)
        
        if contact:
            test_contact_id = contact["id"]
            logger.info(f"✅ Контакт найден: ID={test_contact_id}, Имя={contact.get('name')}")
        else:
            logger.info("❌ Контакт не найден")
            
            # Создадим новый контакт для теста
            logger.info("\n1.2. Создание нового контакта...")
            test_contact_id = client.create_contact(
                name="Тестовый Полный Клиент",
                phone=test_phone,
                email=test_email,
                tg_id=test_tg_id,
                tg_username="@test_full_user"
            )
            logger.info(f"✅ Контакт создан: ID={test_contact_id}")
        
        # ==================== ЭТАП 2: Обновление контакта ====================
        logger.info("\n" + "=" * 80)
        logger.info("ЭТАП 2: Обновление всех полей контакта (⚠️ ЗАКОММЕНТИРОВАНО ДЛЯ ОТЛАДКИ)")
        logger.info("=" * 80)
        
        logger.info("\n⚠️ ЭТАП 2 ПРОПУЩЕН - обновление контакта закомментировано")
        logger.info("   Причина: избежать объединения с существующими контактами")
        
        # logger.info("\n2.1. Обновление через метод update_contact()...")
        # client.update_contact(
        #     contact_id=test_contact_id,
        #     name="Сидоров Сидор Сидорович",
        #     phone="+7test6test9",
        #     email="unique_test_999@example.com",
        #     tg_id="111222333",
        #     tg_username="@sidorov_test"
        # )
        # logger.info("✅ Контакт обновлен")
        
        # # Проверяем обновление
        # logger.info("\n2.2. Проверка обновленных полей контакта...")
        # contact_response = client._make_request("GET", f"/api/v4/contacts/{test_contact_id}")
        # logger.info(f"Имя: {contact_response.get('name')}")
        
        # contact_fields = contact_response.get("custom_fields_values", [])
        # for field in contact_fields:
        #     field_code = field.get("field_code", "")
        #     field_id = field.get("field_id")
        #     values = field.get("values", [])
            
        #     if field_code == "PHONE":
        #         value = values[0].get("value") if values else None
        #         logger.info(f"Телефон: {value}")
        #     elif field_code == "EMAIL":
        #         value = values[0].get("value") if values else None
        #         logger.info(f"Email: {value}")
        #     elif field_id == settings.AMO_CONTACT_FIELD_TG_ID:
        #         value = values[0].get("value") if values else None
        #         logger.info(f"Telegram ID: {value}")
        #     elif field_id == settings.AMO_CONTACT_FIELD_TG_USERNAME:
        #         value = values[0].get("value") if values else None
        #         logger.info(f"Telegram username: {value}")
        
        # ==================== ЭТАП 3: Поиск/Создание сделки ====================
        logger.info("\n" + "=" * 80)
        logger.info("ЭТАП 3: Работа со сделкой")
        logger.info("=" * 80)
        
        logger.info("\n3.1. Поиск активной сделки для контакта...")
        lead = client.find_active_lead(test_contact_id)
        
        if lead:
            test_lead_id = lead["id"]
            logger.info(f"✅ Активная сделка найдена: ID={test_lead_id}, Воронка={lead.get('pipeline_id')}, Название={lead.get('name')}")
        else:
            logger.info("❌ Активная сделка не найдена")
            
            # Создадим новую сделку
            logger.info(f"\n3.2. Создание новой сделки в воронке {settings.AMO_PIPELINE_ID}...")
            
            test_lead_id = client.create_lead(
                name="Тестовая полная сделка",
                contact_id=test_contact_id,
                price=0
            )
            
            logger.info(f"✅ Сделка создана: ID={test_lead_id}")
        
        # ==================== ЭТАП 4: Обновление сделки через update_lead ====================
        logger.info("\n" + "=" * 80)
        logger.info("ЭТАП 4: Обновление сделки (⚠️ ЗАКОММЕНТИРОВАНО ДЛЯ ОТЛАДКИ)")
        logger.info("=" * 80)
        
        logger.info("\n⚠️ ЭТАПЫ 4-7 ПРОПУЩЕНЫ - закомментировано для отладки")
        logger.info(f"   Найденная сделка ID: {test_lead_id if test_lead_id else 'НЕ НАЙДЕНА'}")
        logger.info("   Остановка теста для анализа")
        
        # logger.info("\n4.1. Обновление названия, бюджета и кастомных полей...")
        # client.update_lead(
        #     lead_id=test_lead_id,
        #     name="Тестовая сделка ПОЛНАЯ",
        #     price=45000,
        #     subjects=[1360286, 1360288, 1369170],  # Русский, История, База матем
        #     direction=1373609,  # Направление ЕГЭ
        #     purchase_count=1373537  # 3 покупки
        # )
        # logger.info("✅ Сделка обновлена")
        
        # # Проверяем обновление
        # logger.info("\n4.2. Проверка обновленных полей сделки...")
        # lead_response = client._make_request("GET", f"/api/v4/leads/{test_lead_id}")
        # logger.info(f"Название: {lead_response.get('name')}")
        # logger.info(f"Бюджет: {lead_response.get('price')}")
        # logger.info(f"Pipeline ID: {lead_response.get('pipeline_id')}")
        # logger.info(f"Status ID: {lead_response.get('status_id')}")
        
        # lead_fields = lead_response.get("custom_fields_values", [])
        # if lead_fields:
        #     logger.info("\nКастомные поля сделки:")
        #     for field in lead_fields:
        #         field_id = field.get("field_id")
        #         field_name = field.get("field_name", "Unknown")
        #         values = field.get("values", [])
                
        #         if len(values) > 1:
        #             # Мультисписок
        #             value = ", ".join([v.get("value", "") for v in values])
        #         else:
        #             value = values[0].get("value") if values else None
        #         logger.info(f"  - {field_name} (ID: {field_id}): {value}")
        
        # # ==================== ЭТАП 5: Обновление через update_lead_fields ====================
        # logger.info("\n" + "=" * 80)
        # logger.info("ЭТАП 5: Инкрементальное обновление через update_lead_fields()")
        # logger.info("=" * 80)
        
        # logger.info("\n5.1. Обновление кастомных полей (имитация оплаты)...")
        
        # # Получим текущий счетчик покупок
        # current_purchase_count = 0
        # # for field in lead_fields:
        # #     if field.get("field_id") == settings.AMO_LEAD_FIELD_PURCHASE_COUNT:
        # #         current_purchase_count = int(field["values"][0]["value"]) if field["values"] else 0
        
        # logger.info(f"Текущий счетчик покупок: {current_purchase_count}")
        
        # # НЕ обновляем поля, которых пока нет (закомментированы в settings)
        # client.update_lead_fields(
        #     lead_id=test_lead_id,
        #     subjects=[1360286, 1360290],  # Русский, Английский
        #     direction=1373609,  # Направление ЕГЭ (не меняем, оставляем как было)
        #     # last_payment_amount=5000,  # Поля пока нет
        #     # total_paid_increment=5000,  # Поля пока нет
        #     # payment_status="CONFIRMED",  # Поля пока нет
        #     # last_payment_date="2025-11-21 01:15:00",  # Поля пока нет
        #     # invoice_id="INV-TEST-001",  # Поля пока нет
        #     # payment_id="PAY-TEST-001"  # Поля пока нет
        # )
        # logger.info("✅ Кастомные поля обновлены")
        
#         # Проверяем обновление
#         logger.info("\n5.2. Проверка инкрементального обновления...")
#         lead_response = client._make_request("GET", f"/api/v4/leads/{test_lead_id}")
#         lead_fields = lead_response.get("custom_fields_values", [])
#
#         new_purchase_count = 0
#         if lead_fields:
#             logger.info("\nОбновленные кастомные поля:")
#             for field in lead_fields:
#                 field_id = field.get("field_id")
#                 field_name = field.get("field_name", "Unknown")
#                 values = field.get("values", [])
#
#                 if field_id == settings.AMO_LEAD_FIELD_PURCHASE_COUNT:
#                     new_purchase_count = int(values[0]["value"]) if values else 0
#
#                 if len(values) > 1:
#                     value = ", ".join([v.get("value", "") for v in values])
#                 else:
#                     value = values[0].get("value") if values else None
#                 logger.info(f"  - {field_name} (ID: {field_id}): {value}")
#
#         # logger.info(f"\nСчетчик покупок увеличен: {current_purchase_count} → {new_purchase_count}")
#
#         # ==================== ЭТАП 6: Добавление примечания ====================
#         logger.info("\n" + "=" * 80)
#         logger.info("ЭТАП 6: Добавление примечания")
#         logger.info("=" * 80)
#
#         logger.info("\n6.1. Добавление примечания к сделке...")
#         note_text = """Оплата проведена (ПОЛНЫЙ ТЕСТ)
# Имя клиента: Сидоров Сидор Сидорович
# Дата/время: 2025-11-21 01:15:00
# Сумма: 45000 руб
# Предметы: Русский, Английский
# Направление: ОГЭ
# Источник: platform
# Telegram ID: 111222333
# Telegram username: @sidorov_test"""
#
#         client.add_lead_note(test_lead_id, note_text)
#         logger.info("✅ Примечание добавлено")
#
#         # ==================== ЭТАП 7: Проверка идемпотентности ====================
#         logger.info("\n" + "=" * 80)
#         logger.info("ЭТАП 7: Проверка идемпотентности update_contact_fields()")
#         logger.info("=" * 80)
#
#         logger.info("\n7.1. Попытка обновить уже заполненные поля (должны быть пропущены)...")
#         client.update_contact_fields(
#             contact_id=test_contact_id,
#             tg_id="SHOULD_NOT_UPDATE",
#             tg_username="@should_not_update"
#         )
#         logger.info("✅ Идемпотентность работает (поля не перезаписаны)")
#
#         # Проверяем что поля не изменились
#         logger.info("\n7.2. Проверка что поля остались прежними...")
#         contact_response = client._make_request("GET", f"/api/v4/contacts/{test_contact_id}")
#         contact_fields = contact_response.get("custom_fields_values", [])
#
#         for field in contact_fields:
#             field_id = field.get("field_id")
#             values = field.get("values", [])
#
#             if field_id == settings.AMO_CONTACT_FIELD_TG_ID:
#                 value = values[0].get("value") if values else None
#                 logger.info(f"Telegram ID (не изменился): {value}")
#                 assert value == "111222333", "❌ ОШИБКА: Telegram ID изменился!"
#             elif field_id == settings.AMO_CONTACT_FIELD_TG_USERNAME:
#                 value = values[0].get("value") if values else None
#                 logger.info(f"Telegram username (не изменился): {value}")
#                 assert value == "@sidorov_test", "❌ ОШИБКА: Telegram username изменился!"
#
#         # ==================== ИТОГИ ====================
#         logger.info("\n" + "=" * 80)
#         logger.info("✅✅✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО ✅✅✅")
#         logger.info("=" * 80)
#         logger.info(f"\nТестовый контакт ID: {test_contact_id}")
#         logger.info(f"Тестовая сделка ID: {test_lead_id}")
#         logger.info("\n⚠️ Важно: Воронка для создания сделок берется из AMO_PIPELINE_ID в .env")
#         logger.info("\nПротестированные методы:")
#         logger.info("  ✅ find_contact() - поиск контакта")
#         logger.info("  ✅ create_contact() - создание контакта")
#         logger.info("  ✅ update_contact() - полное обновление контакта")
#         logger.info("  ✅ update_contact_fields() - идемпотентное обновление")
#         logger.info("  ✅ find_active_lead() - поиск активной сделки")
#         logger.info("  ✅ create_lead() - создание сделки")
#         logger.info("  ✅ update_lead() - полное обновление сделки")
#         logger.info("  ✅ update_lead_fields() - инкрементальное обновление")
#         logger.info("  ✅ add_lead_note() - добавление примечания")
#         logger.info("\nПротестированные поля:")
#         logger.info("  Контакт:")
#         logger.info("    ✅ Имя")
#         logger.info("    ✅ Телефон")
#         logger.info("    ✅ Email")
#         logger.info("    ✅ Telegram ID")
#         logger.info("    ✅ Telegram username")
#         logger.info("  Сделка:")
#         logger.info("    ✅ Название")
#         logger.info("    ✅ Бюджет")
#         logger.info("    ✅ Какой предмет выбрал (мультисписок)")
#         logger.info("    ✅ Направления курса (список)")
#         logger.info("    ✅ Купленных курсов (инкрементальный счетчик)")
#         logger.info("\n⚠️  Не протестированы (поля еще не созданы в amoCRM):")
#         logger.info("    ⏸️  Сумма последней оплаты")
#         logger.info("    ⏸️  Общий оплаченный итог")
#         logger.info("    ⏸️  Статус оплаты")
#         logger.info("    ⏸️  Дата/время последней оплаты")
#         logger.info("    ⏸️  Invoice ID")
#         logger.info("    ⏸️  Payment ID")
#
    except Exception as e:
        logger.error("\n" + "=" * 80)
        logger.error(f"❌❌❌ ОШИБКА ТЕСТА ❌❌❌")
        logger.error("=" * 80)
        logger.error(f"\nОшибка: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    test_amocrm_client_full()

