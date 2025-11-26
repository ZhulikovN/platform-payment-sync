"""Тесты для проверки HMAC-подписи вебхука с реальными данными."""

import json
import hmac
import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.core.settings import settings


@pytest.fixture
def real_webhook_data() -> dict:
    """Загрузить реальные данные из amo.json."""
    json_path = Path(__file__).parent / "amo.json"
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def real_webhook_body(real_webhook_data: dict) -> bytes:
    """Конвертировать данные в JSON байты (как приходит от платформы)."""
    return json.dumps(real_webhook_data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


@pytest.fixture
def valid_signature(real_webhook_body: bytes) -> str:
    """Сгенерировать валидную HMAC-SHA256 подпись для реальных данных."""
    return hmac.new(
        key=settings.WEBHOOK_SECRET.encode("utf-8"),
        msg=real_webhook_body,
        digestmod=hashlib.sha256,
    ).hexdigest()


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient."""
    return TestClient(app)


class TestWebhookSignature:
    """Тесты проверки HMAC-подписи с реальными данными из amo.json."""

    def test_signature_generation(self, real_webhook_body: bytes, valid_signature: str):
        """Проверить генерацию подписи (соответствие PHP hash_hmac)."""
        calculated_signature = hmac.new(
            key=settings.WEBHOOK_SECRET.encode("utf-8"),
            msg=real_webhook_body,
            digestmod=hashlib.sha256,
        ).hexdigest()

        assert calculated_signature == valid_signature
        assert len(calculated_signature) == 64
        assert all(c in "0123456789abcdef" for c in calculated_signature)

    def test_webhook_with_valid_signature_mocked(
        self, client: TestClient, real_webhook_body: bytes, valid_signature: str
    ):
        """Проверить, что webhook с валидной подписью проходит аутентификацию (мокируем AmoCRM)."""
        with patch("app.api.webhook_payment.PaymentProcessor") as mock_processor_class:
            mock_processor = AsyncMock()
            mock_processor.process_payment.return_value = AsyncMock(
                status="success",
                message="Payment processed successfully",
                contact_id=60000001,
                lead_id=40000001,
                error=None,
            )
            mock_processor_class.return_value = mock_processor

            response = client.post(
                "/webhook/payment",
                content=real_webhook_body,
                headers={
                    "X-WEBHOOK-SECRET": valid_signature,
                    "Content-Type": "application/json",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "payment_id" in data
            assert data["payment_id"] == "7166790691"

            mock_processor.process_payment.assert_called_once()

    def test_webhook_with_invalid_signature(
        self, client: TestClient, real_webhook_body: bytes
    ):
        """Проверить, что webhook с неверной подписью отклоняется."""
        invalid_signature = "0" * 64

        response = client.post(
            "/webhook/payment",
            content=real_webhook_body,
            headers={
                "X-WEBHOOK-SECRET": invalid_signature,
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 401
        assert "Invalid HMAC signature" in response.json()["detail"]

    def test_webhook_without_signature(self, client: TestClient, real_webhook_body: bytes):
        """Проверить, что webhook без подписи отклоняется."""
        response = client.post(
            "/webhook/payment",
            content=real_webhook_body,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 401
        assert "Missing X-WEBHOOK-SECRET header" in response.json()["detail"]

    def test_signature_is_case_sensitive(
        self, client: TestClient, real_webhook_body: bytes, valid_signature: str
    ):
        """Проверить, что подпись чувствительна к регистру."""
        uppercase_signature = valid_signature.upper()

        response = client.post(
            "/webhook/payment",
            content=real_webhook_body,
            headers={
                "X-WEBHOOK-SECRET": uppercase_signature,
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 401

    def test_signature_changes_with_body_modification(
        self, real_webhook_data: dict, valid_signature: str
    ):
        """Проверить, что изменение тела меняет подпись."""
        modified_data = real_webhook_data.copy()
        modified_data["course_order"]["amount"] = 99999

        modified_body = json.dumps(modified_data, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )

        modified_signature = hmac.new(
            key=settings.WEBHOOK_SECRET.encode("utf-8"),
            msg=modified_body,
            digestmod=hashlib.sha256,
        ).hexdigest()

        assert modified_signature != valid_signature

    def test_webhook_data_parsing(self, real_webhook_data: dict):
        """Проверить, что реальные данные корректно парсятся моделью."""
        from app.models.payment_webhook import PaymentWebhook

        webhook = PaymentWebhook(**real_webhook_data)

        assert webhook.payment_id == "7166790691"
        assert webhook.course_order.status == "CONFIRMED"
        assert webhook.course_order.user.phone == "+7 (964) 080-10-82"
        assert webhook.course_order.user.email == "alex.kazakova2810@mail.ru"
        assert webhook.course_order.user.telegram_id == "1208542295"
        assert webhook.total_cost == 11781
        assert len(webhook.course_order.course_order_items) == 3

    def test_json_encoding_matches_php(self, real_webhook_data: dict):
        """
        Проверить, что Python JSON кодирование совместимо с PHP json_encode.
        
        PHP json_encode по умолчанию:
        - без пробелов между элементами (compact)
        - Unicode символы как \\uXXXX
        - separators: ',' и ':'
        """
        python_json = json.dumps(
            real_webhook_data,
            ensure_ascii=True,
            separators=(",", ":"),
        )

        assert ",  " not in python_json
        assert ":  " not in python_json

        assert "\\u" in python_json

    def test_signature_with_different_json_formatting(self, real_webhook_data: dict):
        """
        Проверить, что разное форматирование JSON дает разные подписи.
        
        ВАЖНО: PHP json_encode и Python request.body() должны давать
        идентичные байты, иначе подписи не совпадут.
        """
        compact_json = json.dumps(
            real_webhook_data, ensure_ascii=True, separators=(",", ":")
        ).encode("utf-8")

        pretty_json = json.dumps(
            real_webhook_data, ensure_ascii=True, indent=2
        ).encode("utf-8")

        unicode_json = json.dumps(
            real_webhook_data, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")

        compact_sig = hmac.new(
            settings.WEBHOOK_SECRET.encode("utf-8"), compact_json, hashlib.sha256
        ).hexdigest()

        pretty_sig = hmac.new(
            settings.WEBHOOK_SECRET.encode("utf-8"), pretty_json, hashlib.sha256
        ).hexdigest()

        unicode_sig = hmac.new(
            settings.WEBHOOK_SECRET.encode("utf-8"), unicode_json, hashlib.sha256
        ).hexdigest()

        assert compact_sig != pretty_sig

        print(f"\nCompact signature: {compact_sig}")
        print(f"Pretty signature:  {pretty_sig}")
        print(f"Unicode signature: {unicode_sig}")

