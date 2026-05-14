import asyncio
import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.config import get_settings
from db.database import get_engine, get_session_factory
from scheduler.jobs import check_and_send_reminders

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    settings = get_settings()

    engine = get_engine(settings.database_url)
    session_factory = get_session_factory(engine)

    bot = Bot(token=settings.bot_token)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_and_send_reminders,
        "interval",
        seconds=30,
        args=[session_factory, bot],
    )
    scheduler.start()

    logger.info("Scheduler started. Checking every 30 seconds.")

    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
