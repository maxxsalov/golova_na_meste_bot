import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import get_settings
from db.database import get_engine, get_session_factory


async def main():
    settings = get_settings()
    logging.basicConfig(level=logging.INFO)

    engine = get_engine(settings.database_url)
    session_factory = get_session_factory(engine)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Import and register routers
    from bot.handlers import registration, reminders, callbacks, misc, inline

    dp.include_router(registration.router)
    dp.include_router(misc.router)
    dp.include_router(callbacks.router)
    dp.include_router(reminders.router)
    dp.include_router(inline.router)

    # Pass session_factory as bot attribute
    bot.session_factory = session_factory

    try:
        await dp.start_polling(bot)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
