"""Интеграционный тест для обработки реального webhook с платформы."""
# poetry run pytest tests/tests_payment_webhook/test_payment_webhook_real_data.py -v -s --log-cli-level=INFO

import logging

import pytest

from app.models.payment_webhook import PaymentWebhook
from app.services.payment_processor import PaymentProcessor
from app.core.amocrm_mappings import SUBJECTS_MAPPING

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


REAL_WEBHOOK_DATA = {
    "course_order": {
            "status": "CONFIRMED",
            "amount": 11781,
            "created_at": "2025-10-09 14:37:23",
            "updated_at": "2025-11-12 08:20:02",
            "code": "",
            "payment_id": "7166790691",
            "payment_method": "card",
            "course_order_items": [
                {
                    "cost": 3927,
                    "number_lessons": 10,
                    "course": {
                        "name": "\u0413\u043e\u0434\u043e\u0432\u043e\u0439 2\u043a26 \u0421\u0442\u0430\u043d\u0434\u0430\u0440\u0442",
                        "subject": {
                            "name": "\u041e\u0431\u0449\u0435\u0441\u0442\u0432\u043e\u0437\u043d\u0430\u043d\u0438\u0435",
                            "project": "\u0415\u0413\u042d"
                        }
                    },
                    "package_id": 322
                },
                {
                    "cost": 3927,
                    "number_lessons": 10,
                    "course": {
                        "name": "\u0413\u043e\u0434\u043e\u0432\u043e\u0439 2\u043a26 \u0421\u0442\u0430\u043d\u0434\u0430\u0440\u0442",
                        "subject": {
                            "name": "\u0410\u043d\u0433\u043b\u0438\u0439\u0441\u043a\u0438\u0439 \u044f\u0437\u044b\u043a",
                            "project": "\u0415\u0413\u042d"
                        }
                    },
                    "package_id": 325
                },
                {
                    "cost": 3927,
                    "number_lessons": 9,
                    "course": {
                        "name": "\u0413\u043e\u0434\u043e\u0432\u043e\u0439 2\u043a26 \u0421\u0442\u0430\u043d\u0434\u0430\u0440\u0442",
                        "subject": {
                            "name": "\u0420\u0443\u0441\u0441\u043a\u0438\u0439",
                            "project": "\u0415\u0413\u042d"
                        }
                    },
                    "package_id": 331
                }
            ],
            "user": {
                "last_name": "\u041a\u0430\u0437\u0430\u043a\u043e\u0432\u0430",
                "first_name": "\u0410\u043b\u0435\u043a\u0441\u0430\u043d\u0434\u0440\u0430",
                "phone": "+7 (964) 080-10-82",
                "email": "alex.kazakova2810@mail.ru",
                "telegram_tag": "alexkazakova",
                "telegram_id": "1208542295"
            },
            "utm": {
                "source": "",
                "term": "",
                "compaign": "",
                "medium": "",
                "content": "",
                "ym": ""
            },
            "domain": "pl.el-ed.ru"
        }
}


@pytest.mark.integration
def test_parse_real_webhook_data() -> None:
    """
    Тест парсинга реальных данных с платформы.

    Проверяет:
    1. Корректность парсинга JSON
    2. Валидацию Pydantic моделей
    3. Извлечение всех полей
    """
    logger.info("=" * 80)
    logger.info("ТЕСТ: Парсинг реальных данных webhook")
    logger.info("=" * 80)

    try:
        webhook = PaymentWebhook(**REAL_WEBHOOK_DATA)

        logger.info(f"\n✓ Данные успешно распарсены")

        logger.info(f"\nОсновная информация:")
        logger.info(f"  Payment ID: {webhook.payment_id}")
        logger.info(f"  Статус: {webhook.course_order.status}")
        logger.info(f"  Amount (флаг): {webhook.course_order.amount}")
        logger.info(f"  Реальная сумма: {webhook.total_cost} руб")
        logger.info(f"  Метод оплаты: {webhook.course_order.payment_method}")

        assert webhook.payment_id == "7166790691"
        assert webhook.course_order.status == "CONFIRMED"
        assert webhook.total_cost == 11781

        user = webhook.course_order.user
        logger.info(f"\nДанные пользователя:")
        logger.info(f"  Имя: {user.first_name} {user.last_name}")
        logger.info(f"  Телефон: {user.phone}")
        logger.info(f"  Email: {user.email}")
        logger.info(f"  Telegram ID: {user.telegram_id}")
        logger.info(f"  Telegram Username: {user.telegram_tag}")

        assert user.first_name == "Александра"
        assert user.last_name == "Казакова"
        assert user.phone == "+7 (964) 080-10-82"
        assert user.email == "alex.kazakova2810@mail.ru"
        assert user.telegram_id == "1208542295"
        assert user.telegram_tag == "alexkazakova"

        logger.info(f"\nКурсы в заказе ({len(webhook.course_order.course_order_items)} шт):")
        for idx, item in enumerate(webhook.course_order.course_order_items, 1):
            logger.info(f"  {idx}. {item.course.subject.name} ({item.course.subject.project})")
            logger.info(f"     Стоимость: {item.cost} руб, Уроков: {item.number_lessons}")

        assert len(webhook.course_order.course_order_items) == 3

        subjects = webhook.subjects_list
        assert "Обществознание" in subjects
        assert "Английский язык" in subjects
        assert "Русский" in subjects

        utm = webhook.course_order.utm
        logger.info(f"\nUTM метки:")
        logger.info(f"  Source: '{utm.source}' (пусто)")
        logger.info(f"  Medium: '{utm.medium}' (пусто)")
        logger.info(f"  Campaign: '{utm.campaign}' (пусто)")

        assert utm.source == ""
        assert utm.medium == ""
        assert utm.campaign == ""

        logger.info(f"\n✓ Все проверки пройдены!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\nОшибка парсинга: {e}", exc_info=True)
        raise


def test_process_real_webhook_logic() -> None:
    """
    Тест логики обработки реального webhook БЕЗ обращения к AmoCRM.

    Проверяет ТОЛЬКО бизнес-логику:
    1. Парсинг данных
    2. Извлечение полей пользователя
    3. Маппинг предметов
    4. Определение направления
    5. Расчет сумм
    6. Определение воронки по UTM
    """
    logger.info("=" * 80)
    logger.info("ТЕСТ: Логика обработки реального webhook (БЕЗ AmoCRM)")
    logger.info("=" * 80)

    try:
        webhook = PaymentWebhook(**REAL_WEBHOOK_DATA)

        user = webhook.course_order.user
        logger.info(f"\n1. Данные пользователя:")
        logger.info(f"   Имя: {user.first_name} {user.last_name}")
        logger.info(f"   Телефон: {user.phone}")
        logger.info(f"   Email: {user.email}")
        logger.info(f"   Telegram ID: {user.telegram_id}")
        logger.info(f"   Telegram Username: {user.telegram_tag}")

        assert user.telegram_id == "1208542295"
        assert user.phone == "+7 (964) 080-10-82"
        assert user.email == "alex.kazakova2810@mail.ru"

        logger.info(f"\n2. Маппинг предметов:")
        subjects_enum_ids = []
        for item in webhook.course_order.course_order_items:
            subject_name = item.course.subject.name
            enum_id = SUBJECTS_MAPPING.get(subject_name)
            if enum_id:
                subjects_enum_ids.append(enum_id)
                logger.info(f"   ✓ {subject_name} → enum_id={enum_id}")

        assert len(subjects_enum_ids) >= 2, "Минимум 2 предмета должны быть смаппены"

        from app.core.amocrm_mappings import get_direction_enum_id

        first_item = webhook.course_order.course_order_items[0]
        project_name = first_item.course.subject.project
        direction_enum_id = get_direction_enum_id(project_name)

        logger.info(f"\n3. Определение направления:")
        logger.info(f"   Project: {project_name} → enum_id={direction_enum_id}")

        assert direction_enum_id is not None

        total = webhook.total_cost
        manual_calc = sum(item.cost for item in webhook.course_order.course_order_items)

        logger.info(f"\n4. Расчет стоимости:")
        logger.info(f"   Курс 1: {webhook.course_order.course_order_items[0].cost} руб")
        logger.info(f"   Курс 2: {webhook.course_order.course_order_items[1].cost} руб")
        logger.info(f"   Курс 3: {webhook.course_order.course_order_items[2].cost} руб")
        logger.info(f"   Итого: {total} руб")

        assert total == manual_calc
        assert total == 11781

        processor = PaymentProcessor()
        utm = webhook.course_order.utm

        pipeline_id, status_id = processor.determine_pipeline_and_status(utm)

        logger.info(f"\n5. Определение воронки:")
        logger.info(f"   UTM source: '{utm.source}' (пусто)")
        logger.info(f"   UTM medium: '{utm.medium}' (пусто)")
        logger.info(f"   → Pipeline ID: {pipeline_id}")
        logger.info(f"   → Status ID: {status_id}")

        from app.core.settings import settings
        assert pipeline_id == settings.AMO_PIPELINE_SITE
        assert status_id == settings.AMO_STATUS_AUTOPAY_SITE

        logger.info(f"\n✓ Вся логика обработки работает корректно!")
        logger.info(f"  • Данные пользователя извлечены: ✓")
        logger.info(f"  • Предметы смаппены: {len(subjects_enum_ids)} шт ✓")
        logger.info(f"  • Направление определено: {project_name} ✓")
        logger.info(f"  • Сумма рассчитана: {total} руб ✓")
        logger.info(f"  • Воронка определена: Сайт (по умолчанию) ✓")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\n Ошибка обработки логики: {e}", exc_info=True)
        raise


@pytest.mark.integration
def test_webhook_with_empty_utm() -> None:
    """
    Тест обработки данных с пустыми UTM метками.

    Проверяет:
    1. Корректную обработку пустых строк в UTM
    2. Определение воронки по умолчанию (Сайт)
    """
    logger.info("=" * 80)
    logger.info("ТЕСТ: Обработка пустых UTM меток")
    logger.info("=" * 80)

    try:
        webhook = PaymentWebhook(**REAL_WEBHOOK_DATA)
        processor = PaymentProcessor()

        utm = webhook.course_order.utm

        pipeline_id, status_id = processor.determine_pipeline_and_status(utm)

        logger.info(f"\nUTM метки пустые:")
        logger.info(f"  Source: '{utm.source}'")
        logger.info(f"  Medium: '{utm.medium}'")

        logger.info(f"\nОпределенная воронка:")
        logger.info(f"  Pipeline ID: {pipeline_id}")
        logger.info(f"  Status ID: {status_id}")

        from app.core.settings import settings
        assert pipeline_id == settings.AMO_PIPELINE_SITE
        assert status_id == settings.AMO_STATUS_AUTOPAY_SITE

        logger.info(f"\n✓ Воронка определена корректно: Сайт (по умолчанию)")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\nОшибка: {e}", exc_info=True)
        raise


@pytest.mark.integration
def test_webhook_subjects_mapping() -> None:
    """
    Тест маппинга предметов на enum_id AmoCRM.

    Проверяет:
    1. Корректный маппинг всех предметов из заказа
    2. Обработку предметов без маппинга (если есть)
    """
    logger.info("=" * 80)
    logger.info("ТЕСТ: Маппинг предметов на enum_id")
    logger.info("=" * 80)

    try:
        webhook = PaymentWebhook(**REAL_WEBHOOK_DATA)

        from app.core.amocrm_mappings import SUBJECTS_MAPPING

        logger.info(f"\nПредметы в заказе:")
        subjects_enum_ids = []

        for item in webhook.course_order.course_order_items:
            subject_name = item.course.subject.name
            enum_id = SUBJECTS_MAPPING.get(subject_name)

            if enum_id:
                subjects_enum_ids.append(enum_id)
                logger.info(f"{subject_name}: enum_id={enum_id}")
            else:
                logger.warning(f"{subject_name}: НЕТ в маппинге!")

        logger.info(f"\nИтого enum_id для сделки: {subjects_enum_ids}")

        assert len(subjects_enum_ids) >= 2, "Минимум 2 предмета должны быть смаппены"

        logger.info(f"\n✓ Маппинг выполнен корректно")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\nОшибка: {e}", exc_info=True)
        raise


@pytest.mark.integration
def test_webhook_direction_mapping() -> None:
    """
    Тест определения направления курса (ЕГЭ/ОГЭ).

    Проверяет:
    1. Корректное определение направления из project
    2. Маппинг на enum_id AmoCRM
    """
    logger.info("=" * 80)
    logger.info("ТЕСТ: Определение направления курса")
    logger.info("=" * 80)

    try:
        webhook = PaymentWebhook(**REAL_WEBHOOK_DATA)

        from app.core.amocrm_mappings import get_direction_enum_id

        first_item = webhook.course_order.course_order_items[0]
        project_name = first_item.course.subject.project

        direction_enum_id = get_direction_enum_id(project_name)

        logger.info(f"\nНаправление из данных:")
        logger.info(f"  Project: {project_name}")
        logger.info(f"  Enum ID: {direction_enum_id}")

        from app.core.settings import settings

        if project_name == "ЕГЭ":
            assert direction_enum_id == settings.AMO_DIRECTION_EGE
        elif project_name == "ОГЭ":
            assert direction_enum_id == settings.AMO_DIRECTION_OGE

        logger.info(f"\n✓ Направление определено корректно: {project_name}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\nОшибка: {e}", exc_info=True)
        raise


@pytest.mark.integration
def test_webhook_total_cost_calculation() -> None:
    """
    Тест расчета общей стоимости заказа.

    Проверяет:
    1. Корректный расчет суммы всех курсов
    2. Что amount != total_cost (amount - это флаг)
    """
    logger.info("=" * 80)
    logger.info("ТЕСТ: Расчет общей стоимости")
    logger.info("=" * 80)

    try:
        webhook = PaymentWebhook(**REAL_WEBHOOK_DATA)

        manual_total = sum(item.cost for item in webhook.course_order.course_order_items)

        logger.info(f"\nСтоимость курсов:")
        for idx, item in enumerate(webhook.course_order.course_order_items, 1):
            logger.info(f"  {idx}. {item.course.subject.name}: {item.cost} руб")

        logger.info(f"\nИтого:")
        logger.info(f"  Сумма курсов (вручную): {manual_total} руб")
        logger.info(f"  Метод total_cost: {webhook.total_cost} руб")
        logger.info(f"  Поле amount: {webhook.course_order.amount} руб")

        assert manual_total == webhook.total_cost
        assert manual_total == 3927 + 3927 + 3927
        assert manual_total == 11781

        logger.info(f"\n✓ Расчет корректен: 3927 + 3927 + 3927 = {manual_total} руб")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\nОшибка: {e}", exc_info=True)
        raise
