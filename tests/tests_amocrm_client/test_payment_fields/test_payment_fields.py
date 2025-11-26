# poetry run pytest tests/tests_amocrm_client/test_payment_fields/test_payment_fields.py -v -s --log-cli-level=INFO

import logging
from datetime import datetime

import pytest

from app.core.amocrm_client import AmoCRMClient
from app.core.settings import settings

logger = logging.getLogger(__name__)

TEST_LEAD_ID = 39437253


@pytest.mark.asyncio
@pytest.mark.integration
async def test_update_lead_fields_payment() -> None:
    """
    Тест обновления кастомных полей оплаты в сделке.
    
    Проверяет:
    1. Обновление полей оплаты (сумма, статус, дата, payment_id)
    2. Корректность записи значений
    3. Что бюджет НЕ изменяется при вызове update_lead_fields()
    """
    logger.info("=" * 80)
    logger.info("ТЕСТ: Обновление кастомных полей оплаты")
    logger.info(f"Тестовая сделка: ID={TEST_LEAD_ID}")
    logger.info("=" * 80)
    
    client = AmoCRMClient()
    
    try:
        logger.info(f"\n{'=' * 80}")
        logger.info("ШАГ 1: Получение текущего состояния сделки")
        logger.info(f"{'=' * 80}")
        
        lead_before = await client._make_request("GET", f"/api/v4/leads/{TEST_LEAD_ID}")
        current_budget = lead_before.get("price", 0) or 0
        logger.info(f"Текущий бюджет сделки: {current_budget} руб")
        
        current_fields = lead_before.get("custom_fields_values") or []
        logger.info(f"\nТекущие значения полей оплаты:")
        
        current_payment_amount = None
        current_payment_status = None
        current_payment_date = None
        current_payment_id = None
        
        for field in current_fields:
            field_id = field.get("field_id")
            field_name = field.get("field_name")
            values = field.get("values", [])
            
            if field_id == settings.AMO_LEAD_FIELD_LAST_PAYMENT_AMOUNT:
                current_payment_amount = values[0].get("value") if values else None
                logger.info(f"  Сумма последней оплаты: {current_payment_amount}")
            elif field_id == settings.AMO_LEAD_FIELD_PAYMENT_STATUS:
                current_payment_status = values[0].get("value") if values else None
                logger.info(f"  Статус оплаты: {current_payment_status}")
            elif field_id == settings.AMO_LEAD_FIELD_LAST_PAYMENT_DATE:
                current_payment_date = values[0].get("value") if values else None
                logger.info(f"  Дата оплаты: {current_payment_date}")
            elif field_id == settings.AMO_LEAD_FIELD_PAYMENT_ID:
                current_payment_id = values[0].get("value") if values else None
                logger.info(f"  Payment ID: {current_payment_id}")
        
        logger.info(f"\n{'=' * 80}")
        logger.info("ШАГ 2: Обновление полей оплаты")
        logger.info(f"{'=' * 80}")
        
        test_amount = 7500
        test_status = "CONFIRMED"
        test_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        test_payment_id = "7999999999"
        
        logger.info(f"Новые значения:")
        logger.info(f"  Сумма: {test_amount} руб")
        logger.info(f"  Статус: {test_status}")
        logger.info(f"  Дата: {test_date}")
        logger.info(f"  Payment ID: {test_payment_id}")
        
        await client.update_lead_fields(
            lead_id=TEST_LEAD_ID,
            last_payment_amount=test_amount,
            payment_status=test_status,
            last_payment_date=test_date,
            payment_id=test_payment_id,
        )
        
        logger.info(f"✓ Поля оплаты обновлены")
        
        logger.info(f"\n{'=' * 80}")
        logger.info("ШАГ 3: Проверка обновленных полей")
        logger.info(f"{'=' * 80}")
        
        lead_after = await client._make_request("GET", f"/api/v4/leads/{TEST_LEAD_ID}")
        new_budget = lead_after.get("price", 0) or 0
        
        logger.info(f"\nБюджет после обновления: {new_budget} руб")
        
        assert new_budget == current_budget, (
            f"Бюджет не должен изменяться при update_lead_fields()! "
            f"Было: {current_budget}, стало: {new_budget}"
        )
        logger.info(f"✓ Бюджет НЕ изменился (как и ожидалось): {current_budget} руб")
        
        updated_fields = lead_after.get("custom_fields_values") or []
        
        new_payment_amount = None
        new_payment_status = None
        new_payment_date = None
        new_payment_id = None
        
        logger.info(f"\nОбновленные поля оплаты:")
        
        for field in updated_fields:
            field_id = field.get("field_id")
            values = field.get("values", [])
            
            if field_id == settings.AMO_LEAD_FIELD_LAST_PAYMENT_AMOUNT:
                new_payment_amount = int(values[0].get("value")) if values else None
                logger.info(f"  Сумма последней оплаты: {new_payment_amount} руб")
            elif field_id == settings.AMO_LEAD_FIELD_PAYMENT_STATUS:
                new_payment_status = int(values[0].get("value")) if values else None
                logger.info(f"  Статус оплаты: {new_payment_status}")
            elif field_id == settings.AMO_LEAD_FIELD_LAST_PAYMENT_DATE:
                new_payment_date = int(values[0].get("value")) if values else None
                logger.info(f"  Дата оплаты: {new_payment_date}")
            elif field_id == settings.AMO_LEAD_FIELD_PAYMENT_ID:
                new_payment_id = int(values[0].get("value")) if values else None
                logger.info(f"  Payment ID: {new_payment_id}")
        
        logger.info(f"\n{'=' * 80}")
        logger.info("ШАГ 4: Проверка корректности обновления")
        logger.info(f"{'=' * 80}")
        
        assert new_payment_amount == test_amount, (
            f"Сумма не обновилась! Ожидалось: {test_amount}, получено: {new_payment_amount}"
        )
        logger.info(f"✓ Сумма последней оплаты обновлена: {test_amount} руб")
        
        expected_status_value = 1
        assert new_payment_status == expected_status_value, (
            f"Статус не обновился! Ожидалось: {expected_status_value}, получено: {new_payment_status}"
        )
        logger.info(f"✓ Статус оплаты обновлен: {expected_status_value} (CONFIRMED)")
        
        assert new_payment_date is not None and new_payment_date > 0, "Дата оплаты не обновилась!"
        logger.info(f"✓ Дата оплаты обновлена: {new_payment_date} (timestamp)")
        
        assert new_payment_id is not None and new_payment_id > 0, "Payment ID не обновился!"
        logger.info(f"✓ Payment ID обновлен: {new_payment_id}")
        
        logger.info(f"\n{'=' * 80}")
        logger.info("ТЕСТ ПРОЙДЕН: Кастомные поля оплаты обновляются корректно")
        logger.info("Бюджет НЕ изменяется при update_lead_fields()")
        logger.info(f"{'=' * 80}")
        
    except Exception as e:
        logger.error(f"\nОшибка в тесте: {e}", exc_info=True)
        raise


@pytest.mark.asyncio
@pytest.mark.integration
async def test_update_lead_budget() -> None:
    """
    Тест записи бюджета через update_lead_fields().
    
    Проверяет:
    1. Бюджет устанавливается в указанное значение
    2. Значение записывается напрямую (НЕ прибавляется)
    3. Кастомные поля оплаты НЕ изменяются при обновлении только бюджета
    """
    logger.info("=" * 80)
    logger.info("ТЕСТ: Запись бюджета (общий оплаченный итог)")
    logger.info(f"Тестовая сделка: ID={TEST_LEAD_ID}")
    logger.info("=" * 80)
    
    client = AmoCRMClient()
    
    try:
        logger.info(f"\n{'=' * 80}")
        logger.info("ШАГ 1: Получение текущего бюджета")
        logger.info(f"{'=' * 80}")
        
        lead_before = await client._make_request("GET", f"/api/v4/leads/{TEST_LEAD_ID}")
        current_budget = lead_before.get("price", 0) or 0
        logger.info(f"Текущий бюджет: {current_budget} руб")
        
        current_fields = lead_before.get("custom_fields_values") or []
        current_payment_id = None
        
        for field in current_fields:
            if field.get("field_id") == settings.AMO_LEAD_FIELD_PAYMENT_ID:
                values = field.get("values", [])
                current_payment_id = values[0].get("value") if values else None
                logger.info(f"Текущий Payment ID: {current_payment_id}")
                break
        
        logger.info(f"\n{'=' * 80}")
        logger.info("ШАГ 2: Установка бюджета (общий оплаченный итог)")
        logger.info(f"{'=' * 80}")
        
        new_budget_value = 10000
        
        logger.info(f"Новое значение бюджета: {new_budget_value} руб")
        
        await client.update_lead_fields(lead_id=TEST_LEAD_ID, total_paid=new_budget_value)
        
        logger.info(f"✓ Бюджет обновлен")
        
        logger.info(f"\n{'=' * 80}")
        logger.info("ШАГ 3: Проверка обновленного бюджета")
        logger.info(f"{'=' * 80}")
        
        lead_after = await client._make_request("GET", f"/api/v4/leads/{TEST_LEAD_ID}")
        new_budget = lead_after.get("price", 0) or 0
        
        logger.info(f"Новый бюджет: {new_budget} руб")
        
        assert new_budget == new_budget_value, (
            f"Бюджет записался неправильно! "
            f"Ожидалось: {new_budget_value}, получено: {new_budget}"
        )
        logger.info(f"✓ Бюджет установлен корректно: {new_budget} руб")
        
        updated_fields = lead_after.get("custom_fields_values") or []
        new_payment_id = None
        
        for field in updated_fields:
            if field.get("field_id") == settings.AMO_LEAD_FIELD_PAYMENT_ID:
                values = field.get("values", [])
                new_payment_id = values[0].get("value") if values else None
                break
        
        assert new_payment_id == current_payment_id, (
            f"Payment ID не должен изменяться при обновлении только бюджета! "
            f"Было: {current_payment_id}, стало: {new_payment_id}"
        )
        logger.info(f"✓ Payment ID НЕ изменился (как и ожидалось): {current_payment_id}")
        
        logger.info(f"\n{'=' * 80}")
        logger.info("ТЕСТ ПРОЙДЕН: Бюджет записывается напрямую через update_lead_fields()")
        logger.info("Кастомные поля НЕ изменяются при обновлении только бюджета")
        logger.info(f"{'=' * 80}")
        
    except Exception as e:
        logger.error(f"\nОшибка в тесте: {e}", exc_info=True)
        raise
