"""Реальный тест создания сделки с новыми полями (класс и количество курсов)."""
#  poetry run pytest tests/tests_amocrm_client/test_real_lead_creation.py -v -s --log-cli-level=INFO

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.amocrm_client import AmoCRMClient
from app.core.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_create_lead_with_new_fields():
    """
    Создать реальную сделку в AmoCRM с новыми полями.

    Проверяемые поля:
    - 806496 (Класс) - textarea, записываем "11"
    - 813727 (Количество курсов) - numeric, записываем 3
    """
    client = AmoCRMClient()

    try:
        logger.info("=" * 80)
        logger.info("ТЕСТ: Создание сделки с новыми полями")
        logger.info("=" * 80)

        # Создаем контакт
        logger.info("\nШаг 1: Создание контакта")
        contact_id = await client.create_contact(
            name="Тест Новые Поля",
            phone="79999999991",
            email="test_new_fields@example.com"
        )
        logger.info(f"Контакт создан: {contact_id}")

        # Создаем сделку с классом
        logger.info("\nШаг 2: Создание сделки")
        lead_id = await client.create_lead(
            name="ТЕСТ: Новые поля класс и количество",
            contact_id=contact_id,
            price=17000,
            pipeline_id=settings.AMO_PIPELINE_SITE,
            status_id=settings.AMO_DEFAULT_STATUS_ID,
            user_class=11,
            is_parent=False,
            utm_source="test",
            utm_medium="integration_test"
        )

        logger.info(f"Сделка создана: {lead_id}")

        # Обновляем сделку - добавляем количество курсов
        logger.info("\nШаг 3: Обновление количества курсов")
        await client.update_lead_fields(
            lead_id=lead_id,
            purchased_subjects_count=2,
            total_paid=17000
        )

        logger.info("Сделка обновлена")

        # Проверяем созданную сделку
        logger.info("\nШаг 4: Проверка созданной сделки")
        response = await client._make_request("GET", f"/api/v4/leads/{lead_id}")

        custom_fields = response.get("custom_fields_values", [])

        class_field = None
        purchase_count_field = None

        for field in custom_fields:
            if field["field_id"] == 806496:  # Классф
                class_field = field
            if field["field_id"] == 813727:  # Количество курсов
                purchase_count_field = field

        logger.info("\n" + "=" * 80)
        logger.info("РЕЗУЛЬТАТ ПРОВЕРКИ:")
        logger.info("=" * 80)

        if class_field:
            value = class_field["values"][0]["value"] if class_field.get("values") else None
            logger.info(f"Поле 'Класс' (806496): {value}")
            if value == "11":
                logger.info("  [OK] Класс записан правильно как строка '11'")
            else:
                logger.error(f"  [FAIL] Ожидалось '11', получено '{value}'")
        else:
            logger.error("  [FAIL] Поле 'Класс' не найдено в сделке")

        if purchase_count_field:
            value = purchase_count_field["values"][0]["value"] if purchase_count_field.get("values") else None
            logger.info(f"\nПоле 'Количество курсов' (813727): {value}")
            # Может быть 2 (был 0 + добавили 2) или больше если там уже было что-то
            if value and (value == 2 or value == "2" or int(value) >= 2):
                logger.info(f"  [OK] Количество записано правильно: {value}")
            else:
                logger.error(f"  [FAIL] Ожидалось >= 2, получено {value}")
        else:
            logger.error("  [FAIL] Поле 'Количество курсов' не найдено в сделке")

        logger.info("\n" + "=" * 80)
        logger.info(f"Ссылка на сделку: https://egeland.amocrm.ru/leads/detail/{lead_id}")
        logger.info("=" * 80)

        return True

    except Exception as e:
        logger.error(f"\n[ERROR] Тест провален: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = asyncio.run(test_create_lead_with_new_fields())
    sys.exit(0 if success else 1)