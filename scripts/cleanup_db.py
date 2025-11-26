#!/usr/bin/env python3
"""Скрипт для очистки старых записей из БД payment_events."""

import asyncio
import logging
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.event_logger import EventLogger

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    """Удалить записи старше 30 дней."""
    try:
        event_logger = EventLogger()
        
        logger.info("Удаление записей старше 30 дней...")
        deleted = await event_logger.cleanup_old_records(days=30)
        logger.info(f"Удалено записей: {deleted}")
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
