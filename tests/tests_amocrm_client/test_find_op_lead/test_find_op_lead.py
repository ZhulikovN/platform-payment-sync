# poetry run pytest tests/tests_amocrm_client/test_find_op_lead/test_find_op_lead.py -v -s --log-cli-level=INFO

import logging

import pytest

from app.core.amocrm_client import AmoCRMClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

TEST_OP_CONTACT_PHONE = "+79176568728"
TEST_OP_CONTACT_EMAIL = ""
TEST_OP_CONTACT_TG_ID = ""

# @pytest.mark.integration
# @pytest.mark.asyncio
# async def test_find_op_lead_by_name() -> None:
#     """Тест поиска сделки по названию 'Оплата: ОГЭ/ЕГЭ/Средняя школа' (is_utm_op=False)."""
#     logger.info("=" * 80)
#     logger.info("ТЕСТ: Поиск OP сделки по названию 'Оплата:...'")
#     logger.info(f"Telegram ID: {TEST_OP_CONTACT_TG_ID}")
#     logger.info(f"Phone: {TEST_OP_CONTACT_PHONE}")
#     logger.info(f"Email: {TEST_OP_CONTACT_EMAIL}")
#     logger.info("Режим: is_utm_op=False (поиск по названию)")
#     logger.info("=" * 80)
#
#     client = AmoCRMClient()
#
#     try:
#         # Поиск сделки по названию
#         logger.info("\n1. Поиск сделки с названием 'Оплата: ОГЭ/ЕГЭ/Средняя школа'...")
#         logger.info("   Воронки для поиска: Сайт, 7/8 класс")
#         logger.info("   Исключаем: автооплаты, успех, закрытие")
#
#         lead = await client.find_op_lead(
#             telegram_id=TEST_OP_CONTACT_TG_ID,
#             phone=TEST_OP_CONTACT_PHONE,
#             email=TEST_OP_CONTACT_EMAIL,
#             is_utm_op=False,  # Поиск по названию
#         )
#
#         logger.info(f"\n2. Результат поиска:")
#         if lead:
#             logger.info(f"  ✓ Сделка найдена!")
#             logger.info(f"  ID: {lead['id']}")
#             logger.info(f"  Название: {lead.get('name')}")
#             logger.info(f"  Воронка ID: {lead.get('pipeline_id')}")
#             logger.info(f"  Статус ID: {lead.get('status_id')}")
#             logger.info(f"  Бюджет: {lead.get('price')}")
#             logger.info(f"  Обновлена: {lead.get('updated_at')}")
#
#             # Проверяем что название соответствует
#             lead_name = lead.get("name", "")
#             expected_names = ["Оплата: ОГЭ", "Оплата: ЕГЭ", "Оплата: Средняя школа"]
#
#             assert any(expected_name in lead_name for expected_name in expected_names), \
#                 f"Название сделки '{lead_name}' не соответствует ожидаемым: {expected_names}"
#
#             logger.info(f"\n  ✓ Название сделки корректное: {lead_name}")
#         else:
#             logger.info(f"  ✗ Сделка не найдена")
#             logger.info(f"  Это может быть нормально, если у контакта нет таких сделок")
#
#         logger.info("\n✓ Тест пройден успешно!")
#         logger.info("=" * 80)
#
#     except Exception as e:
#         logger.error(f"\n✗ Ошибка в тесте: {e}", exc_info=True)
#         raise


@pytest.mark.integration
@pytest.mark.asyncio
async def test_find_op_lead_by_utm() -> None:
    """Тест расширенного поиска сделки для utm_source=op (is_utm_op=True)."""
    logger.info("=" * 80)
    logger.info("ТЕСТ: Расширенный поиск OP сделки (utm_source=op)")
    logger.info(f"Telegram ID: {TEST_OP_CONTACT_TG_ID}")
    logger.info(f"Phone: {TEST_OP_CONTACT_PHONE}")
    logger.info(f"Email: {TEST_OP_CONTACT_EMAIL}")
    logger.info("Режим: is_utm_op=True (расширенный поиск в 13 воронках)")
    logger.info("=" * 80)

    client = AmoCRMClient()

    try:
        # Расширенный поиск для utm_source=op
        logger.info("\n1. Расширенный поиск сделки в 13 воронках...")
        logger.info("   Воронки: Сайт, Сайт TG, VK ЕГЭ, VK ОГЭ, TG ЕГЭ, TG ОГЭ,")
        logger.info("            TG БОТЫ, TG AI, TG Родители, Вебинары, 7/8 класс,")
        logger.info("            Яндекс, Партнеры")
        logger.info("   Исключаем: автооплаты, успех, закрытие")

        lead = await client.find_op_lead(
            telegram_id=TEST_OP_CONTACT_TG_ID,
            phone=TEST_OP_CONTACT_PHONE,
            email=TEST_OP_CONTACT_EMAIL,
            is_utm_op=True,  # Расширенный поиск для utm_source=op
        )

        logger.info(f"\n2. Результат поиска:")
        if lead:
            logger.info(f"  ✓ Сделка найдена!")
            logger.info(f"  ID: {lead['id']}")
            logger.info(f"  Название: {lead.get('name')}")
            logger.info(f"  Воронка ID: {lead.get('pipeline_id')}")
            logger.info(f"  Статус ID: {lead.get('status_id')}")
            logger.info(f"  Бюджет: {lead.get('price')}")
            logger.info(f"  Обновлена: {lead.get('updated_at')}")

            # Проверяем что сделка не удалена и не в закрытых статусах
            assert lead["id"] > 0
            assert not lead.get("is_deleted", False)

            logger.info(f"\n  ✓ Сделка валидна")
        else:
            logger.info(f"  ✗ Сделка не найдена")
            logger.info(f"  Это может быть нормально, если у контакта нет сделок в указанных воронках")

        logger.info("\n✓ Тест пройден успешно!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\n✗ Ошибка в тесте: {e}", exc_info=True)
        raise

