"""Тесты для метода determine_pipeline_and_status в PaymentProcessor."""
# poetry run pytest tests/tests_payment_processor/test_determine_pipeline.py -v -s --log-cli-level=INFO

import logging

import pytest

from app.services.payment_processor import PaymentProcessor
from app.core.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


class TestDeterminePipeline:
    """Тесты для определения воронки и этапа по UTM меткам."""

    def setup_method(self) -> None:
        """Инициализация перед каждым тестом."""
        self.processor = PaymentProcessor()

    def test_empty_utm_goes_to_site(self) -> None:
        """Тест: Пустые UTM → воронка Сайт."""
        logger.info("=" * 80)
        logger.info("ТЕСТ: Пустые UTM метки")
        logger.info("=" * 80)

        utm = {"source": "", "medium": ""}

        pipeline_id, status_id = self.processor.determine_pipeline_and_status(utm)

        logger.info(f"\nUTM: {utm}")
        logger.info(f"Результат:")
        logger.info(f"  Pipeline ID: {pipeline_id}")
        logger.info(f"  Status ID: {status_id}")

        assert pipeline_id == settings.AMO_PIPELINE_SITE
        assert status_id == settings.AMO_STATUS_AUTOPAY_SITE

        logger.info(f"\n✓ Корректно: Сайт → Автооплаты ООО")
        logger.info("=" * 80)

    def test_yandex_medium_cpc(self) -> None:
        """Тест: utm_medium=cpc → воронка Сайт Яндекс."""
        logger.info("=" * 80)
        logger.info("ТЕСТ: utm_medium=cpc (Яндекс)")
        logger.info("=" * 80)

        utm = {"source": "", "medium": "cpc"}

        pipeline_id, status_id = self.processor.determine_pipeline_and_status(utm)

        logger.info(f"\nUTM: {utm}")
        logger.info(f"Результат:")
        logger.info(f"  Pipeline ID: {pipeline_id}")
        logger.info(f"  Status ID: {status_id}")

        assert pipeline_id == settings.AMO_PIPELINE_YANDEX
        assert status_id == settings.AMO_STATUS_AUTOPAY_YANDEX

        logger.info(f"\n✓ Корректно: Сайт Яндекс → Автооплаты ООО")
        logger.info("=" * 80)

    def test_yandex_medium_el_ege(self) -> None:
        """Тест: utm_medium=el-ege → воронка Сайт Яндекс."""
        logger.info("=" * 80)
        logger.info("ТЕСТ: utm_medium=el-ege (Яндекс)")
        logger.info("=" * 80)

        utm = {"source": "", "medium": "el-ege"}

        pipeline_id, status_id = self.processor.determine_pipeline_and_status(utm)

        logger.info(f"\nUTM: {utm}")
        logger.info(f"Результат:")
        logger.info(f"  Pipeline ID: {pipeline_id}")
        logger.info(f"  Status ID: {status_id}")

        assert pipeline_id == settings.AMO_PIPELINE_YANDEX
        assert status_id == settings.AMO_STATUS_AUTOPAY_YANDEX

        logger.info(f"\n✓ Корректно: Сайт Яндекс → Автооплаты ООО")
        logger.info("=" * 80)

    def test_yandex_medium_cpm(self) -> None:
        """Тест: utm_medium=cpm → воронка Сайт Яндекс."""
        logger.info("=" * 80)
        logger.info("ТЕСТ: utm_medium=cpm (Яндекс)")
        logger.info("=" * 80)

        utm = {"source": "", "medium": "cpm"}

        pipeline_id, status_id = self.processor.determine_pipeline_and_status(utm)

        logger.info(f"\nUTM: {utm}")
        logger.info(f"Результат:")
        logger.info(f"  Pipeline ID: {pipeline_id}")
        logger.info(f"  Status ID: {status_id}")

        assert pipeline_id == settings.AMO_PIPELINE_YANDEX
        assert status_id == settings.AMO_STATUS_AUTOPAY_YANDEX

        logger.info(f"\n✓ Корректно: Сайт Яндекс → Автооплаты ООО")
        logger.info("=" * 80)

    def test_partner_advcake(self) -> None:
        """Тест: utm_source=advcake → воронка ПАРТНЕРЫ."""
        logger.info("=" * 80)
        logger.info("ТЕСТ: utm_source=advcake (Партнеры)")
        logger.info("=" * 80)

        utm = {"source": "advcake", "medium": ""}

        pipeline_id, status_id = self.processor.determine_pipeline_and_status(utm)

        logger.info(f"\nUTM: {utm}")
        logger.info(f"Результат:")
        logger.info(f"  Pipeline ID: {pipeline_id}")
        logger.info(f"  Status ID: {status_id}")

        assert pipeline_id == settings.AMO_PIPELINE_PARTNERS
        assert status_id == settings.AMO_STATUS_AUTOPAY_PARTNERS

        logger.info(f"\n✓ Корректно: ПАРТНЕРЫ → Автооплаты ООО")
        logger.info("=" * 80)

    def test_partner_flocktory(self) -> None:
        """Тест: utm_source=flocktory → воронка ПАРТНЕРЫ."""
        logger.info("=" * 80)
        logger.info("ТЕСТ: utm_source=flocktory (Партнеры)")
        logger.info("=" * 80)

        utm = {"source": "flocktory", "medium": ""}

        pipeline_id, status_id = self.processor.determine_pipeline_and_status(utm)

        assert pipeline_id == settings.AMO_PIPELINE_PARTNERS
        assert status_id == settings.AMO_STATUS_AUTOPAY_PARTNERS

        logger.info(f"\n✓ Корректно: ПАРТНЕРЫ → Автооплаты ООО")
        logger.info("=" * 80)

    def test_partner_tutortop(self) -> None:
        """Тест: utm_source=tutortop → воронка ПАРТНЕРЫ."""
        utm = {"source": "tutortop", "medium": ""}
        pipeline_id, status_id = self.processor.determine_pipeline_and_status(utm)

        assert pipeline_id == settings.AMO_PIPELINE_PARTNERS
        assert status_id == settings.AMO_STATUS_AUTOPAY_PARTNERS

    def test_partner_sravni(self) -> None:
        """Тест: utm_source=sravni → воронка ПАРТНЕРЫ."""
        utm = {"source": "sravni", "medium": ""}
        pipeline_id, status_id = self.processor.determine_pipeline_and_status(utm)

        assert pipeline_id == settings.AMO_PIPELINE_PARTNERS
        assert status_id == settings.AMO_STATUS_AUTOPAY_PARTNERS

    def test_partner_tbank(self) -> None:
        """Тест: utm_source=tbank → воронка ПАРТНЕРЫ."""
        utm = {"source": "tbank", "medium": ""}
        pipeline_id, status_id = self.processor.determine_pipeline_and_status(utm)

        assert pipeline_id == settings.AMO_PIPELINE_PARTNERS
        assert status_id == settings.AMO_STATUS_AUTOPAY_PARTNERS

    def test_partner_reshuege(self) -> None:
        """Тест: utm_source=reshuege → воронка ПАРТНЕРЫ."""
        utm = {"source": "reshuege", "medium": ""}
        pipeline_id, status_id = self.processor.determine_pipeline_and_status(utm)

        assert pipeline_id == settings.AMO_PIPELINE_PARTNERS
        assert status_id == settings.AMO_STATUS_AUTOPAY_PARTNERS

    def test_partner_ris_promo(self) -> None:
        """Тест: utm_source=ris.promo → воронка ПАРТНЕРЫ."""
        utm = {"source": "ris.promo", "medium": ""}
        pipeline_id, status_id = self.processor.determine_pipeline_and_status(utm)

        assert pipeline_id == settings.AMO_PIPELINE_PARTNERS
        assert status_id == settings.AMO_STATUS_AUTOPAY_PARTNERS

    def test_partner_gdeslon(self) -> None:
        """Тест: utm_source=gdeslon → воронка ПАРТНЕРЫ."""
        utm = {"source": "gdeslon", "medium": ""}
        pipeline_id, status_id = self.processor.determine_pipeline_and_status(utm)

        assert pipeline_id == settings.AMO_PIPELINE_PARTNERS
        assert status_id == settings.AMO_STATUS_AUTOPAY_PARTNERS

    def test_partner_admitad(self) -> None:
        """Тест: utm_source=admitad → воронка ПАРТНЕРЫ."""
        utm = {"source": "admitad", "medium": ""}
        pipeline_id, status_id = self.processor.determine_pipeline_and_status(utm)

        assert pipeline_id == settings.AMO_PIPELINE_PARTNERS
        assert status_id == settings.AMO_STATUS_AUTOPAY_PARTNERS

    def test_partner_pfm(self) -> None:
        """Тест: utm_source=pfm → воронка ПАРТНЕРЫ."""
        utm = {"source": "pfm", "medium": ""}
        pipeline_id, status_id = self.processor.determine_pipeline_and_status(utm)

        assert pipeline_id == settings.AMO_PIPELINE_PARTNERS
        assert status_id == settings.AMO_STATUS_AUTOPAY_PARTNERS

    def test_priority_partners_over_yandex(self) -> None:
        """Тест: Приоритет ПАРТНЕРЫ выше чем Яндекс."""
        logger.info("=" * 80)
        logger.info("ТЕСТ: Приоритет - ПАРТНЕРЫ выше Яндекс")
        logger.info("=" * 80)

        # Если utm_source совпадает с партнером, даже если utm_medium=cpc
        utm = {"source": "advcake", "medium": "cpc"}

        pipeline_id, status_id = self.processor.determine_pipeline_and_status(utm)

        logger.info(f"\nUTM: {utm}")
        logger.info(f"Результат:")
        logger.info(f"  Pipeline ID: {pipeline_id}")
        logger.info(f"  Status ID: {status_id}")

        assert pipeline_id == settings.AMO_PIPELINE_PARTNERS
        assert status_id == settings.AMO_STATUS_AUTOPAY_PARTNERS

        logger.info(f"\n✓ Корректно: ПАРТНЕРЫ (приоритет выше чем Яндекс)")
        logger.info("=" * 80)

    def test_case_insensitive(self) -> None:
        """Тест: Регистр не важен."""
        logger.info("=" * 80)
        logger.info("ТЕСТ: Регистронезависимость")
        logger.info("=" * 80)

        utm1 = {"source": "ADVCAKE", "medium": ""}
        pipeline_id1, status_id1 = self.processor.determine_pipeline_and_status(utm1)

        utm2 = {"source": "advcake", "medium": ""}
        pipeline_id2, status_id2 = self.processor.determine_pipeline_and_status(utm2)

        utm3 = {"source": "AdVcAkE", "medium": ""}
        pipeline_id3, status_id3 = self.processor.determine_pipeline_and_status(utm3)

        logger.info(f"\nUTM 1 (ВЕРХНИЙ): {utm1} → Pipeline: {pipeline_id1}")
        logger.info(f"UTM 2 (нижний): {utm2} → Pipeline: {pipeline_id2}")
        logger.info(f"UTM 3 (СмЕшАнНыЙ): {utm3} → Pipeline: {pipeline_id3}")

        assert pipeline_id1 == pipeline_id2 == pipeline_id3 == settings.AMO_PIPELINE_PARTNERS
        assert status_id1 == status_id2 == status_id3 == settings.AMO_STATUS_AUTOPAY_PARTNERS

        logger.info(f"\n✓ Корректно: Все варианты → ПАРТНЕРЫ")
        logger.info("=" * 80)

    def test_partial_match_in_source(self) -> None:
        """Тест: Частичное совпадение в utm_source."""
        logger.info("=" * 80)
        logger.info("ТЕСТ: Частичное совпадение в utm_source")
        logger.info("=" * 80)

        utm = {"source": "special_advcake_campaign", "medium": ""}

        pipeline_id, status_id = self.processor.determine_pipeline_and_status(utm)

        logger.info(f"\nUTM: {utm}")
        logger.info(f"Результат:")
        logger.info(f"  Pipeline ID: {pipeline_id}")
        logger.info(f"  Status ID: {status_id}")

        assert pipeline_id == settings.AMO_PIPELINE_PARTNERS
        assert status_id == settings.AMO_STATUS_AUTOPAY_PARTNERS

        logger.info(f"\n✓ Корректно: 'advcake' найден в строке → ПАРТНЕРЫ")
        logger.info("=" * 80)

    def test_unknown_utm_goes_to_site(self) -> None:
        """Тест: Неизвестные UTM → воронка Сайт (по умолчанию)."""
        logger.info("=" * 80)
        logger.info("ТЕСТ: Неизвестные UTM метки")
        logger.info("=" * 80)

        utm = {"source": "unknown_source", "medium": "unknown_medium"}

        pipeline_id, status_id = self.processor.determine_pipeline_and_status(utm)

        logger.info(f"\nUTM: {utm}")
        logger.info(f"Результат:")
        logger.info(f"  Pipeline ID: {pipeline_id}")
        logger.info(f"  Status ID: {status_id}")

        assert pipeline_id == settings.AMO_PIPELINE_SITE
        assert status_id == settings.AMO_STATUS_AUTOPAY_SITE

        logger.info(f"\n✓ Корректно: Неизвестные UTM → Сайт (по умолчанию)")
        logger.info("=" * 80)

    def test_all_partners_summary(self) -> None:
        """Тест: Проверка всех партнеров одним тестом."""
        logger.info("=" * 80)
        logger.info("ТЕСТ: Все партнеры (summary)")
        logger.info("=" * 80)

        partners = [
            "advcake", "flocktory", "tutortop", "sravni", "tbank",
            "reshuege", "ris.promo", "gdeslon", "admitad", "pfm"
        ]

        logger.info(f"\nПроверка {len(partners)} партнеров:")

        for partner in partners:
            utm = {"source": partner, "medium": ""}
            pipeline_id, status_id = self.processor.determine_pipeline_and_status(utm)

            assert pipeline_id == settings.AMO_PIPELINE_PARTNERS, f"Партнер {partner} должен идти в ПАРТНЕРЫ"
            assert status_id == settings.AMO_STATUS_AUTOPAY_PARTNERS

            logger.info(f"  ✓ {partner:15} → ПАРТНЕРЫ")

        logger.info(f"\n✓ Все {len(partners)} партнеров работают корректно!")
        logger.info("=" * 80)

    def test_all_yandex_mediums_summary(self) -> None:
        """Тест: Проверка всех Яндекс medium одним тестом."""
        logger.info("=" * 80)
        logger.info("ТЕСТ: Все Яндекс mediums (summary)")
        logger.info("=" * 80)

        yandex_mediums = ["cpc", "el-ege", "cpm"]

        logger.info(f"\nПроверка {len(yandex_mediums)} Яндекс mediums:")

        for medium in yandex_mediums:
            utm = {"source": "", "medium": medium}
            pipeline_id, status_id = self.processor.determine_pipeline_and_status(utm)

            assert pipeline_id == settings.AMO_PIPELINE_YANDEX, f"Medium {medium} должен идти в Сайт Яндекс"
            assert status_id == settings.AMO_STATUS_AUTOPAY_YANDEX

            logger.info(f"  ✓ utm_medium={medium:10} → Сайт Яндекс")

        logger.info(f"\n✓ Все {len(yandex_mediums)} mediums работают корректно!")
        logger.info("=" * 80)
