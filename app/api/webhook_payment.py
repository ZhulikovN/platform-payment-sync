"""Webhook endpoint для приема данных об оплатах с платформы."""

import asyncio
from asyncio import Semaphore
import hashlib
import hmac
import json
import logging
import time

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
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


async def process_payment_batch_parallel(
    payments: list[PaymentWebhook],
    processor: PaymentProcessor,
) -> dict:
    """
    Параллельная обработка батча оплат с контролем rate limit.

    Использует asyncio.gather для параллельной обработки с ограничением
    через Semaphore для соблюдения rate limit AmoCRM (7 запросов/сек).

    Каждая оплата делает ~6 API запросов (матчинг + обновление).
    Semaphore(1) = 1 оплата одновременно = ~6 запросов/сек (безопасно).

    Для 1000 оплат время обработки: ~60-70 минут.

    Args:
        payments: Список оплат для обработки
        processor: PaymentProcessor для обработки

    Returns:
        Результаты обработки с детальной статистикой
    """
    logger.info("=" * 80)
    logger.info(f"Starting PARALLEL batch processing: {len(payments)} payments")
    logger.info(f"Rate limit: 1 concurrent task (AmoCRM safe mode: ~6 req/sec)")
    logger.info("=" * 80)

    if not payments:
        logger.warning("Empty payments list received")
        return {
            "status": "success",
            "message": "No payments to process",
            "total": 0,
            "succeeded": 0,
            "failed": 0,
            "duplicates": 0,
            "skipped": 0,
            "elapsed_seconds": 0,
            "results": [],
        }

    semaphore = Semaphore(1)

    start_time = time.time()

    async def process_one(payment: PaymentWebhook, idx: int) -> dict:
        """
        Обработать одну оплату с ограничением через semaphore.

        Args:
            payment: Данные об оплате
            idx: Индекс элемента (для логирования)

        Returns:
            Результат обработки
        """
        async with semaphore:
            payment_id = payment.payment_id or f"batch_{idx}"

            try:
                logger.info(
                    f"[{idx}/{len(payments)}] Processing payment_id={payment_id}, "
                    f"amount={payment.total_cost}, user={payment.course_order.user.phone}"
                )

                result = await processor.process_payment(payment)

                if result.status == "success":
                    logger.info(
                        f"[{idx}/{len(payments)}] ✓ SUCCESS: {payment_id} -> "
                        f"contact {result.contact_id}, lead {result.lead_id}"
                    )
                    return {
                        "payment_id": payment_id,
                        "status": "success",
                        "contact_id": result.contact_id,
                        "lead_id": result.lead_id,
                    }

                elif result.status == "duplicate":
                    logger.info(f"[{idx}/{len(payments)}] ⊗ DUPLICATE: {payment_id}")
                    return {
                        "payment_id": payment_id,
                        "status": "duplicate",
                        "message": result.message,
                    }

                elif result.status == "skipped":
                    logger.info(f"[{idx}/{len(payments)}] ⊘ SKIPPED: {payment_id} - {result.message}")
                    return {
                        "payment_id": payment_id,
                        "status": "skipped",
                        "message": result.message,
                    }

                else:
                    logger.warning(f"[{idx}/{len(payments)}] ⚠ {result.status.upper()}: {payment_id} - {result.message}")
                    return {
                        "payment_id": payment_id,
                        "status": result.status,
                        "message": result.message,
                    }

            except Exception as e:
                logger.error(
                    f"[{idx}/{len(payments)}] ✗ ERROR processing {payment_id}: {e}",
                    exc_info=True,
                )
                return {
                    "payment_id": payment_id,
                    "status": "error",
                    "error": str(e),
                }

    logger.info("Starting parallel execution...")

    all_results = await asyncio.gather(
        *[process_one(payment, idx) for idx, payment in enumerate(payments, start=1)],
        return_exceptions=True,
    )

    succeeded = 0
    failed = 0
    duplicates = 0
    skipped = 0
    results = []

    for result in all_results:
        if isinstance(result, dict):
            results.append(result)
            result_status = result.get("status")
            if result_status == "success":
                succeeded += 1
            elif result_status == "duplicate":
                duplicates += 1
            elif result_status == "skipped":
                skipped += 1
            elif result_status in ("error", "contact_not_found", "lead_not_found"):
                failed += 1
        elif isinstance(result, Exception):
            logger.error(f"Unhandled exception in task: {result}")
            failed += 1
            results.append({"payment_id": None, "status": "error", "error": str(result)})

    elapsed_time = time.time() - start_time
    items_per_sec = len(payments) / elapsed_time if elapsed_time > 0 else 0

    logger.info("=" * 80)
    logger.info("PARALLEL batch processing COMPLETED")
    logger.info(f"Total time: {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes)")
    logger.info(f"Speed: {items_per_sec:.2f} payments/sec")
    logger.info(f"Results: {succeeded} succeeded, {duplicates} duplicates, {skipped} skipped, {failed} failed")
    logger.info("=" * 80)

    return {
        "status": "completed",
        "message": f"Processed {len(payments)} payments in {elapsed_time:.1f}s",
        "total": len(payments),
        "succeeded": succeeded,
        "failed": failed,
        "duplicates": duplicates,
        "skipped": skipped,
        "elapsed_seconds": int(elapsed_time),
        "elapsed_minutes": round(elapsed_time / 60, 1),
        "items_per_second": round(items_per_sec, 2),
        "results": results,
    }


@router.post("/payment-batch")
async def receive_payment_batch(
    request: Request,
    background_tasks: BackgroundTasks,
    x_webhook_secret: str = Header(None, alias="X-WEBHOOK-SECRET", description="HMAC-SHA256 подпись тела запроса"),
    processor: PaymentProcessor = Depends(get_payment_processor),
) -> JSONResponse:
    """
    Batch endpoint для массовой обработки оплат (до 1000 за раз).

    Принимает массив оплат, обрабатывает параллельно в фоновом режиме
    с контролем rate limit для AmoCRM API.

    Обработка выполняется асинхронно - endpoint сразу возвращает 202 Accepted.
    Результаты можно отслеживать через логи.

    Аутентификация: HMAC-SHA256 подпись в заголовке X-WEBHOOK-SECRET

    Args:
        request: FastAPI Request для получения сырого тела
        background_tasks: FastAPI background tasks для фоновой обработки
        x_webhook_secret: HMAC-SHA256 подпись тела запроса (hex строка)
        processor: PaymentProcessor для обработки оплат (dependency injection)

    Returns:
        JSONResponse с подтверждением принятия задачи

    Raises:
        HTTPException: 401 если подпись неверная
        HTTPException: 400 если данные некорректные или батч > 1000
    """
    logger.info("=" * 80)
    logger.info("Received BATCH webhook request")
    logger.info("=" * 80)

    body = await request.body()

    logger.debug(f"Request body size: {len(body)} bytes")

    if not x_webhook_secret:
        logger.error("Missing X-WEBHOOK-SECRET header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-WEBHOOK-SECRET header",
        )

    logger.info("Verifying HMAC-SHA256 signature...")
    if not verify_hmac_signature(body, x_webhook_secret, settings.WEBHOOK_SECRET):
        logger.warning("Invalid HMAC signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid HMAC signature",
        )

    logger.info("✓ HMAC signature verified successfully")

    try:
        payload_list = json.loads(body.decode("utf-8"))

        if not isinstance(payload_list, list):
            logger.error("Expected array of payments, got single object")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Expected array of payments. Use /webhook/payment for single payment.",
            )

        if len(payload_list) > 1000:
            logger.error(f"Batch size {len(payload_list)} exceeds limit of 1000")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Batch size exceeds limit of 1000 payments",
            )

        payments = [PaymentWebhook(**item) for item in payload_list]

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON: {str(e)}",
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}",
        ) from e

    logger.info("=" * 80)
    logger.info(f"Batch validation successful: {len(payments)} payments")
    logger.info("=" * 80)

    background_tasks.add_task(process_payment_batch_parallel, payments, processor)

    estimated_minutes = len(payments) * 4 / 60

    logger.info(f"Task accepted for background processing. Estimated time: {estimated_minutes:.1f} minutes")

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "status": "accepted",
            "message": f"Processing {len(payments)} payments in background",
            "total": len(payments),
            "estimated_time_minutes": round(estimated_minutes, 1),
            "note": "Processing is asynchronous. Check logs for results.",
        },
    )


@router.get("/health")
async def health_check() -> JSONResponse:
    """
    Health check endpoint для мониторинга работоспособности сервиса.

    Returns:
        JSONResponse со статусом сервиса
    """

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "healthy",
            "service": "platform-payment-sync",
            "version": "7.0.0",
            "endpoints": {
                "single": "/webhook/payment",
                "batch": "/webhook/payment-batch (up to 1000)",
            },
        },
    )
