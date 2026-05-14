import datetime

from aiogram import Router, types
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import async_sessionmaker

from db.repository import Repository


def _format_utc_to_local(utc_dt: datetime.datetime, tz_offset_minutes: int) -> str:
    tz = datetime.timezone(datetime.timedelta(minutes=tz_offset_minutes))
    local_dt = utc_dt.astimezone(tz)
    return local_dt.strftime("%H:%M")

router = Router()


def _get_session_factory(event: types.TelegramObject) -> async_sessionmaker:
    return event.bot.session_factory


@router.message(Command("reg"))
async def cmd_register(message: types.Message) -> None:
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Напиши: /reg Имя\nНапример: /reg Антон")
        return

    display_name = parts[1].strip()
    session_factory = _get_session_factory(message)

    async with session_factory() as session:
        repo = Repository(session)
        chat_id = await repo.get_or_create_chat(message.chat.id)
        user_id = await repo.get_or_create_user(
            message.from_user.id, message.from_user.full_name,
        )
        await repo.register_member(chat_id, user_id, display_name)
        await session.commit()

    await message.answer(f"Запомнил! Теперь ты <b>{display_name}</b>.")
    await message.answer(
        "💡 Совет: чтобы создать напоминание, просто напиши "
        "«напомни мне через 30 мин позвонить»\n"
        "Все команды: /help"
    )


@router.message(Command("who"))
async def cmd_whoami(message: types.Message) -> None:
    session_factory = _get_session_factory(message)

    async with session_factory() as session:
        repo = Repository(session)
        member = await repo.get_member_by_telegram_id(
            message.chat.id, message.from_user.id,
        )
        if not member:
            await message.answer("Ты ещё не зарегистрирован. Напиши: /reg Имя")
            return
        chat = await repo.get_chat_by_telegram_id(message.chat.id)
        await session.commit()

    tz_offset_minutes = chat.tz_offset_minutes if chat else 180
    quiet_status = ""
    if member.quiet_until:
        local_time = _format_utc_to_local(member.quiet_until, tz_offset_minutes)
        quiet_status = f"\n🔇 Тихий режим до {local_time}"

    await message.answer(f"Ты <b>{member.display_name}</b>.{quiet_status}")
