"""Главное FastAPI приложение для приема webhook от платформы оплаты."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.webhook_payment import router as webhook_router
from app.core.settings import settings

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Platform Payment Sync",
    description="Сервис для автоматической фиксации оплат из платформы pl.el-ed.ru в amoCRM",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router)

logger.info("=" * 80)
logger.info("Platform Payment Sync Service started")
logger.info(f"Log level: {settings.LOG_LEVEL}")
logger.info(f"AmoCRM Base URL: {settings.AMO_BASE_URL}")
logger.info(f"Target Pipeline ID: {settings.AMO_PIPELINE_ID}")
logger.info(f"CREATE_IF_NOT_FOUND: {settings.CREATE_IF_NOT_FOUND}")
logger.info(f"Allowed CORS origins: {settings.ALLOWED_ORIGINS}")
logger.info("=" * 80)


@app.get("/")
async def root() -> dict[str, str]:
    """Корневой endpoint."""
    return {
        "service": "Platform Payment Sync",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )
