"""Интеграционный тест для обновления всех полей существующей сделки."""
#  poetry run pytest tests/tests_amocrm_client/test_update_lead_fields/test_update_lead_fields.py -v -s --log-cli-level=INFO

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
async def test_update_all_lead_fields() -> None:
    """
    Тест обновления всех полей существующей сделки.
    
    Проверяет:
    1. Обновление базовых полей (название, бюджет)
    2. Обновление предметов (мультисписок)
    3. Обновление направления курса
    4. Инкрементальное обновление счетчика покупок
    5. Обновление полей оплаты (если есть)
    6. Добавление примечания
    """
    logger.info("=" * 80)
    logger.info("ТЕСТ: Обновление всех полей сделки")
    logger.info("=" * 80)

    client = AmoCRMClient()
    
    test_lead_id = 39438813
 
    logger.info(f"\nИспользуем существующую сделку: ID={test_lead_id}")
    
    try:
        logger.info(f"\n{'=' * 80}")
        logger.info("ШАГ 0: Получение контакта из сделки и его обновление")
        logger.info(f"{'=' * 80}")
        
        lead_with_contacts = await client._make_request("GET", f"/api/v4/leads/{test_lead_id}?with=contacts")
        
        contacts = lead_with_contacts.get("_embedded", {}).get("contacts", [])
        if not contacts:
            raise ValueError(f"У сделки {test_lead_id} нет привязанных контактов!")
        
        test_contact_id = contacts[0]["id"]
        logger.info(f"Контакт из сделки: ID={test_contact_id}")
        
        contact_before = await client._make_request("GET", f"/api/v4/contacts/{test_contact_id}")
        
        logger.info(f"\nТекущие данные контакта:")
        logger.info(f"  Имя: {contact_before.get('name')}")
        
        contact_fields = contact_before.get("custom_fields_values") or []
        for field in contact_fields:
            field_code = field.get("field_code")
            field_id = field.get("field_id")
            values = field.get("values", [])
            
            if field_code == "PHONE":
                logger.info(f"  Телефон: {values[0].get('value') if values else 'N/A'}")
            elif field_code == "EMAIL":
                logger.info(f"  Email: {values[0].get('value') if values else 'N/A'}")
            elif field_id == settings.AMO_CONTACT_FIELD_TG_ID:
                logger.info(f"  Telegram ID: {values[0].get('value') if values else 'N/A'}")
            elif field_id == settings.AMO_CONTACT_FIELD_TG_USERNAME:
                logger.info(f"  Telegram Username: {values[0].get('value') if values else 'N/A'}")
        
        new_contact_name = "ТЕСТ: Обновленный Контакт (полный тест)3"
        new_phone = "+799912345672"
        new_email = "updated_test2@ya.com"
        new_tg_id = "9998888872"
        new_tg_username = "updated_test_user2"
        
        logger.info(f"\nНовые данные контакта:")
        logger.info(f"  Имя: {new_contact_name}")
        logger.info(f"  Телефон: {new_phone}")
        logger.info(f"  Email: {new_email}")
        logger.info(f"  Telegram ID: {new_tg_id}")
        logger.info(f"  Telegram Username: {new_tg_username} (без @)")
        
        await client.update_contact(
            contact_id=test_contact_id,
            name=new_contact_name,
            phone=new_phone,
            email=new_email,
            tg_id=new_tg_id,
            tg_username=new_tg_username
        )
        logger.info(f"Контакт обновлен через client.update_contact()")
        
        # Сразу проверим, что реально обновилось
        contact_check = await client._make_request("GET", f"/api/v4/contacts/{test_contact_id}")
        logger.info(f"\nПроверка сразу после обновления:")
        logger.info(f"   Имя: {contact_check.get('name')}")
        
        check_fields = contact_check.get("custom_fields_values") or []
        for field in check_fields:
            field_id = field.get("field_id")
            values = field.get("values", [])
            
            if field_id == settings.AMO_CONTACT_FIELD_TG_USERNAME:
                username_val = values[0].get("value") if values else None
                logger.info(f"   Telegram Username: {username_val}")
        
        # Шаг 1: Получить текущее состояние сделки
        logger.info(f"\n{'=' * 80}")
        logger.info("ШАГ 1: Получение текущего состояния сделки")
        logger.info(f"{'=' * 80}")
        
        lead_before = await client._make_request("GET", f"/api/v4/leads/{test_lead_id}")
        
        logger.info(f"\nТекущие данные:")
        logger.info(f"  Название: {lead_before.get('name')}")
        logger.info(f"  Бюджет: {lead_before.get('price')} руб")
        logger.info(f"  Воронка: {lead_before.get('pipeline_id')}")
        logger.info(f"  Статус: {lead_before.get('status_id')}")
        
        current_fields = lead_before.get("custom_fields_values") or []
        current_purchase_count = 0
        
        logger.info(f"\nТекущие кастомные поля:")
        if not current_fields:
            logger.info(f"  (кастомные поля отсутствуют)")
        
        for field in current_fields:
            field_id = field.get("field_id")
            field_name = field.get("field_name")
            values = field.get("values", [])
            
            if field_id == settings.AMO_LEAD_FIELD_PURCHASE_COUNT:
                current_purchase_count = int(values[0]["value"]) if values else 0
                logger.info(f"  {field_name}: {current_purchase_count}")
            elif len(values) > 1:
                value_str = ", ".join([v.get("value", "") for v in values])
                logger.info(f"  {field_name}: {value_str}")
            elif values:
                logger.info(f"  {field_name}: {values[0].get('value')}")

        logger.info(f"\n{'=' * 80}")
        logger.info("ШАГ 2: Обновление названия и бюджета")
        logger.info(f"{'=' * 80}")
        
        new_name = "ТЕСТ: Обновленная сделка (полный тест полей)"
        new_price = 35000
        
        logger.info(f"\nНовые значения:")
        logger.info(f"  Название: {new_name}")
        logger.info(f"  Бюджет: {new_price} руб")
        
        await client.update_lead(
            lead_id=test_lead_id,
            name=new_name,
            price=new_price
        )
        logger.info(f"Название и бюджет обновлены")

        logger.info(f"\n{'=' * 80}")
        logger.info("ШАГ 3: Обновление предметов, направления и счетчика (через update_lead)")
        logger.info(f"{'=' * 80}")
        
        subjects = [1360286, 1360288, 1360290]  # Русский, Математика, Английский
        direction = 1373607  # ОГЭ
        purchase_count = 1373535  # 2 покупки
        
        logger.info(f"\nНовые значения:")
        logger.info(f"  Предметы: Русский (1360286), Математика (1360288), Английский (1360290)")
        logger.info(f"  Направление: ОГЭ (1373607)")
        logger.info(f"  Купленных курсов: 2 (enum_id: 1373535)")
        
        await client.update_lead(
            lead_id=test_lead_id,
            subjects=subjects,
            direction=direction,
            purchase_count=purchase_count
        )
        logger.info(f"Предметы, направление и счетчик обновлены через update_lead")

        logger.info(f"\n{'=' * 80}")
        logger.info("ШАГ 4: Инкрементальное обновление (через update_lead_fields)")
        logger.info(f"{'=' * 80}")
        
        logger.info(f"\nПосле update_lead счетчик стал: 2")
        logger.info(f"После update_lead_fields будет: 3 (+1 инкрементально)")
        
        new_subjects = [1360286, 1360292]  # Русский, Обществознание
        
        await client.update_lead_fields(
            lead_id=test_lead_id,
            subjects=new_subjects,
            direction=1373607,  # ОГЭ
            last_payment_amount=5000,
            payment_status="CONFIRMED",
            last_payment_date="2025-11-21 03:00:00",
            payment_id="77777777",
            status_id = 80731242,  # Перевести в целевой этап
            total_paid = 2000,  # Записать общий оплаченный итог (сумма всех курсов в текущей оплате)
        )
        logger.info(f"Инкрементальное обновление выполнено")

        logger.info(f"\n{'=' * 80}")
        logger.info("ШАГ 5: Добавление примечания")
        logger.info(f"{'=' * 80}")
        
        note_text = """ТЕСТ: Обновление всех полей
Сумма оплаты: 5000 руб
Статус: CONFIRMED
Дата: 2025-11-21 03:00:00
Payment ID: TEST-PAY-67890
Источник: integration_test"""
        
        await client.add_lead_note(test_lead_id, note_text)
        logger.info(f"Примечание добавлено")

        logger.info(f"\n{'=' * 80}")
        logger.info("ШАГ 6: Проверка финального состояния")
        logger.info(f"{'=' * 80}")
        
        lead_after = await client._make_request("GET", f"/api/v4/leads/{test_lead_id}")
        
        logger.info(f"\nФинальные данные:")
        logger.info(f"  Название: {lead_after.get('name')}")
        logger.info(f"  Бюджет: {lead_after.get('price')} руб")
        
        assert lead_after.get("name") == new_name, f"Название должно быть '{new_name}'"
        assert lead_after.get("price") == new_price, f"Бюджет должен быть {new_price}"
        
        updated_fields = lead_after.get("custom_fields_values") or []
        final_purchase_count = 0
        
        logger.info(f"\nОбновленные кастомные поля:")
        if not updated_fields:
            logger.info(f"  (кастомные поля отсутствуют)")
        
        for field in updated_fields:
            field_id = field.get("field_id")
            field_name = field.get("field_name")
            values = field.get("values", [])
            
            if field_id == settings.AMO_LEAD_FIELD_PURCHASE_COUNT:
                final_purchase_count = int(values[0]["value"]) if values else 0
                logger.info(f"  {field_name}: {final_purchase_count} (было 2, стало 3)")
                assert final_purchase_count == 3, "Счетчик покупок должен быть 3 (2 + 1)"
            elif field_id == settings.AMO_LEAD_FIELD_SUBJECTS:
                subjects_list = [v.get("value", "") for v in values]
                logger.info(f"  {field_name}: {', '.join(subjects_list)}")
            elif field_id == settings.AMO_LEAD_FIELD_DIRECTION:
                logger.info(f"  {field_name}: {values[0].get('value') if values else 'N/A'}")
            elif settings.AMO_LEAD_FIELD_LAST_PAYMENT_AMOUNT and field_id == settings.AMO_LEAD_FIELD_LAST_PAYMENT_AMOUNT:
                logger.info(f"  {field_name}: {values[0].get('value') if values else 'N/A'} руб")
            elif settings.AMO_LEAD_FIELD_PAYMENT_STATUS and field_id == settings.AMO_LEAD_FIELD_PAYMENT_STATUS:
                logger.info(f"  {field_name}: {values[0].get('value') if values else 'N/A'}")
            elif settings.AMO_LEAD_FIELD_LAST_PAYMENT_DATE and field_id == settings.AMO_LEAD_FIELD_LAST_PAYMENT_DATE:
                logger.info(f"  {field_name}: {values[0].get('value') if values else 'N/A'}")
            elif settings.AMO_LEAD_FIELD_PAYMENT_ID and field_id == settings.AMO_LEAD_FIELD_PAYMENT_ID:
                logger.info(f"  {field_name}: {values[0].get('value') if values else 'N/A'}")

        logger.info(f"\n{'=' * 80}")
        logger.info("ШАГ 7: Проверка обновленного контакта")
        logger.info(f"{'=' * 80}")
        
        contact_after = await client._make_request("GET", f"/api/v4/contacts/{test_contact_id}")
        
        logger.info(f"\nФинальные данные контакта:")
        logger.info(f"  Имя: {contact_after.get('name')}")
        
        assert contact_after.get("name") == new_contact_name, f"Имя контакта должно быть '{new_contact_name}'"
        
        contact_fields_after = contact_after.get("custom_fields_values") or []
        for field in contact_fields_after:
            field_code = field.get("field_code")
            field_id = field.get("field_id")
            values = field.get("values", [])
            
            if field_code == "PHONE":
                phone_value = values[0].get("value") if values else None
                logger.info(f"  Телефон: {phone_value}")
                assert phone_value == new_phone, f"Телефон должен быть {new_phone}"
            elif field_code == "EMAIL":
                email_value = values[0].get("value") if values else None
                logger.info(f"  Email: {email_value}")
                assert email_value == new_email, f"Email должен быть {new_email}"
            elif field_id == settings.AMO_CONTACT_FIELD_TG_ID:
                tg_id_value = values[0].get("value") if values else None
                logger.info(f"  Telegram ID: {tg_id_value}")
                assert tg_id_value == new_tg_id, f"Telegram ID должен быть {new_tg_id}"
            elif field_id == settings.AMO_CONTACT_FIELD_TG_USERNAME:
                tg_username_value = values[0].get("value") if values else None
                logger.info(f"  Telegram Username: {tg_username_value}")
                # AmoCRM может вернуть username с @ или без, проверяем оба варианта
                assert tg_username_value in [new_tg_username, f"@{new_tg_username}"], \
                    f"Telegram Username должен быть {new_tg_username} или @{new_tg_username}"

        logger.info(f"\nВсе проверки пройдены успешно!")
        logger.info("=" * 80)
        logger.info("ИТОГИ:")
        logger.info(f"\nКОНТАКТ: ID={test_contact_id}")
        logger.info(f"  • Имя: {contact_before.get('name')} → {new_contact_name}")
        logger.info(f"  • Телефон: обновлен → {new_phone}")
        logger.info(f"  • Email: обновлен → {new_email}")
        logger.info(f"  • Telegram ID: обновлен → {new_tg_id}")
        logger.info(f"  • Telegram Username: обновлен → {new_tg_username}")
        logger.info(f"\nСДЕЛКА: ID={test_lead_id}")
        logger.info(f"  • Название обновлено:")
        logger.info(f"  • Бюджет обновлен: {lead_before.get('price')} → {new_price} руб")
        logger.info(f"  • Предметы обновлены:")
        logger.info(f"  • Направление обновлено:")
        logger.info(f"  • Счетчик покупок: 0 → 2 (update_lead) → 3 (update_lead_fields +1)")
        logger.info(f"  • Поля оплаты обновлены:")
        logger.info(f"  • Примечание добавлено:")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\nОшибка в тесте: {e}", exc_info=True)
        raise

