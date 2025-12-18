"""Webhook endpoint для приема данных об оплатах с платформы."""

import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.core.settings import settings
from app.models.payment_webhook import PaymentWebhook
from app.services.payment_processor import PaymentProcessor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])


def get_payment_processor() -> PaymentProcessor:
    """Dependency injection для PaymentProcessor."""
    return PaymentProcessor()


def verify_hmac_signature(body: bytes, signature: str, secret: str) -> bool:
    """
    Проверить HMAC-SHA256 подпись запроса.

    Соответствует PHP коду:
    hash_hmac('sha256', json_encode($jsonBody), $key)

    Args:
        body: Тело запроса (сырые байты)
        signature: Подпись из заголовка (hex строка)
        secret: Секретный ключ

    Returns:
        True если подпись верна, False если нет
    """
    logger.debug(f"Verifying HMAC with key: {secret[:5]}...{secret[-5:]}")
    logger.debug(f"Body length: {len(body)} bytes")

    expected_signature = hmac.new(
        key=secret.encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    logger.debug(f"Expected signature: {expected_signature}")
    logger.debug(f"Received signature: {signature}")

    is_valid = hmac.compare_digest(expected_signature, signature)

    if is_valid:
        logger.debug("Signatures match")
    else:
        logger.debug("Signatures do not match")

    return is_valid


@router.post("/payment")
async def receive_payment_webhook(
    request: Request,
    x_webhook_secret: str = Header(None, alias="X-WEBHOOK-SECRET", description="HMAC-SHA256 подпись тела запроса"),
    processor: PaymentProcessor = Depends(get_payment_processor),
) -> JSONResponse:
    """
    Webhook endpoint для приема данных об успешных оплатах с платформы.

    Аутентификация: HMAC-SHA256 подпись в заголовке X-WEBHOOK-SECRET

    Args:
        request: FastAPI Request для получения сырого тела
        x_webhook_secret: HMAC-SHA256 подпись тела запроса (hex строка)
        processor: PaymentProcessor для обработки оплаты (dependency injection)

    Returns:
        JSONResponse с результатом обработки

    Raises:
        HTTPException: 401 если подпись неверная
        HTTPException: 400 если данные некорректные
        HTTPException: 409 если оплата уже обработана (дубликат)
        HTTPException: 404 если контакт/сделка не найдены (при CREATE_IF_NOT_FOUND=False)
        HTTPException: 500 при внутренней ошибке
    """
    logger.info("=" * 80)
    logger.info("Received webhook request")
    logger.info("=" * 80)

    body = await request.body()

    logger.debug(f"Request body size: {len(body)} bytes")
    logger.debug(f"Request body preview: {body[:200].decode('utf-8', errors='ignore')}...")

    if not x_webhook_secret:
        logger.error("Missing X-WEBHOOK-SECRET header")
        logger.error("Available headers: %s", dict(request.headers))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-WEBHOOK-SECRET header",
        )

    logger.info(f"Received signature: {x_webhook_secret[:20]}...{x_webhook_secret[-20:]}")
    logger.debug(f"Full signature: {x_webhook_secret}")

    logger.info("Verifying HMAC-SHA256 signature...")
    if not verify_hmac_signature(body, x_webhook_secret, settings.WEBHOOK_SECRET):
        logger.warning("Invalid HMAC signature")
        logger.warning(f"Expected key: {settings.WEBHOOK_SECRET[:5]}...{settings.WEBHOOK_SECRET[-5:]}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid HMAC signature",
        )

    logger.info("✓ HMAC signature verified successfully")

    try:
        payload_dict = json.loads(body.decode("utf-8"))
        payload = PaymentWebhook(**payload_dict)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON: {str(e)}",
        ) from e
    except Exception as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}",
        ) from e

    payment_id = payload.payment_id or "unknown"
    amount = payload.total_cost
    user_name = f"{payload.course_order.user.first_name} {payload.course_order.user.last_name}".strip()
    phone = payload.course_order.user.phone
    email = payload.course_order.user.email

    logger.info("=" * 80)
    logger.info("Payment webhook data parsed successfully")
    logger.info("=" * 80)
    logger.info(f"Payment ID: {payment_id}")
    logger.info(f"Amount: {amount} {payload.course_order.currency}")
    logger.info(f"Status: {payload.course_order.status}")
    logger.info(f"User: {user_name}")
    logger.info(f"Phone: {phone}")
    logger.info(f"Email: {email}")
    logger.info(f"Telegram ID: {payload.course_order.user.telegram_id or 'not provided'}")
    logger.info(f"Telegram tag: {payload.course_order.user.telegram_tag or 'not provided'}")
    logger.info(f"Subjects: {payload.subjects_str}")
    logger.info(f"Payment method: {payload.course_order.payment_method or 'not specified'}")
    logger.info(f"UTM source: {payload.course_order.utm.source or 'not specified'}")
    logger.info(f"UTM medium: {payload.course_order.utm.medium or 'not specified'}")
    logger.info(f"UTM campaign: {payload.course_order.utm.campaign or 'not specified'}")
    logger.info("=" * 80)

    logger.info("Starting payment processing...")
    result = await processor.process_payment(payload)
    logger.info(f"Payment processing completed: status={result.status}")

    if result.status == "success":
        logger.info(f"Payment processed successfully: contact_id={result.contact_id}, lead_id={result.lead_id}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "message": result.message,
                "payment_id": payment_id,
                "contact_id": result.contact_id,
                "lead_id": result.lead_id,
            },
        )

    if result.status == "duplicate":
        logger.warning(f"Payment duplicate detected: {payment_id}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=result.message,
        )

    if result.status == "contact_not_found":
        logger.error(f"Contact not found for payment: {payment_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.message,
        )

    if result.status == "lead_not_found":
        logger.error(f"Lead not found for payment: {payment_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.message,
        )

    if result.status == "skipped":
        logger.info(f"Payment skipped: {payment_id} - {result.message}")
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "status": "skipped",
                "message": result.message,
                "payment_id": payment_id,
            },
        )

    logger.error(f"Payment processing error: {payment_id} - {result.error}")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=result.error or "Internal server error",
    )


@router.get("/health")
async def health_check() -> JSONResponse:
    """
    Health check endpoint для мониторинга работоспособности сервиса.

    Returns:
        JSONResponse со статусом сервиса
    """
    # TODO: Добавить проверку доступности amoCRM API
    # TODO: Добавить проверку доступности БД SQLite

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "healthy",
            "service": "platform-payment-sync",
            "version": "6.0.0",
        },
    )
