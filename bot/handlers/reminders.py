import datetime
import logging

from aiogram import Router, types
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.parser import parse_message
from db.repository import Repository

router = Router()
logger = logging.getLogger(__name__)


def _format_utc_to_local(utc_dt: datetime.datetime, tz_offset_minutes: int) -> str:
    tz = datetime.timezone(datetime.timedelta(minutes=tz_offset_minutes))
    local_dt = utc_dt.astimezone(tz)
    return local_dt.strftime("%H:%M %d.%m")


def _resolve_recipient_member(
    sender_member_id: int,
    other_member: "ChatMember | None",
    recipient_keyword: str,
) -> int | None:
    if recipient_keyword == "мне":
        return sender_member_id
    if recipient_keyword in ("ей", "ему") and other_member:
        return other_member.id
    if recipient_keyword in ("нам", "всем"):
        return None
    return None


@router.message(Command("my"))
async def cmd_my_reminders(message: types.Message) -> None:
    session_factory: async_sessionmaker = message.bot.session_factory

    async with session_factory() as session:
        repo = Repository(session)
        member = await repo.get_member_by_telegram_id(
            message.chat.id, message.from_user.id,
        )
        if not member:
            await message.answer("Ты ещё не зарегистрирован. Напиши: /reg Имя")
            return

        reminders = await repo.get_active_reminders_for_member(member.id)
        chat = await repo.get_chat_by_telegram_id(message.chat.id)
        await session.commit()

    tz_offset_minutes = chat.tz_offset_minutes if chat else 180

    if not reminders:
        await message.answer("У тебя нет активных напоминаний.")
        return

    lines = []
    for r in reminders:
        time_str = _format_utc_to_local(r.remind_at, tz_offset_minutes)
        lines.append(f"#{r.id} ⏰ {time_str} — {r.text}")

    await message.answer("📋 Твои напоминания:\n\n" + "\n".join(lines))


@router.message(Command("our"))
async def cmd_our_reminders(message: types.Message) -> None:
    session_factory: async_sessionmaker = message.bot.session_factory

    async with session_factory() as session:
        repo = Repository(session)
        member = await repo.get_member_by_telegram_id(
            message.chat.id, message.from_user.id,
        )
        if not member:
            await message.answer("Ты ещё не зарегистрирован. Напиши: /reg Имя")
            return

        reminders = await repo.get_incoming_reminders(member.id)
        chat = await repo.get_chat_by_telegram_id(message.chat.id)
        await session.commit()

    tz_offset_minutes = chat.tz_offset_minutes if chat else 180

    if not reminders:
        await message.answer("Нет напоминаний от партнёра.")
        return

    lines = []
    for r in reminders:
        time_str = _format_utc_to_local(r.remind_at, tz_offset_minutes)
        lines.append(f"#{r.id} ⏰ {time_str} — {r.text}")

    await message.answer("📋 Напоминания от партнёра:\n\n" + "\n".join(lines))


@router.message(Command("del"))
async def cmd_cancel_reminder(message: types.Message) -> None:
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Напиши: /del ID\nНапример: /del 42")
        return

    try:
        reminder_id = int(parts[1].strip())
    except ValueError:
        await message.answer("ID должен быть числом. Например: /del 42")
        return

    session_factory: async_sessionmaker = message.bot.session_factory

    async with session_factory() as session:
        repo = Repository(session)
        member = await repo.get_member_by_telegram_id(
            message.chat.id, message.from_user.id,
        )
        if not member:
            await message.answer("Ты ещё не зарегистрирован. Напиши: /reg Имя")
            return

        ok = await repo.cancel_reminder(reminder_id, member.id)
        await session.commit()

    if ok:
        await message.answer(f"✔️ Напоминание #{reminder_id} отменено.")
    else:
        await message.answer(f"Не удалось отменить #{reminder_id}. Проверь ID.")


@router.message()
async def handle_reminder_message(message: types.Message) -> None:
    if not message.text:
        return

    from bot.content import match_russian_command
    hint = match_russian_command(message.text)
    if hint:
        await message.answer(f"Я не знаю такую команду. Попробуй: {hint}")
        return

    session_factory: async_sessionmaker = message.bot.session_factory

    async with session_factory() as session:
        repo = Repository(session)
        chat = await repo.get_chat_by_telegram_id(message.chat.id)
        if not chat:
            chat_id = await repo.get_or_create_chat(message.chat.id)
            tz_offset_minutes = 180
        else:
            chat_id = chat.id
            tz_offset_minutes = chat.tz_offset_minutes

    parsed = parse_message(message.text, tz_offset_minutes=tz_offset_minutes)
    if not parsed:
        return

    async with session_factory() as session:
        repo = Repository(session)

        chat_id = await repo.get_or_create_chat(message.chat.id)
        user_id = await repo.get_or_create_user(
            message.from_user.id, message.from_user.full_name,
        )
        sender_member_id = await repo.register_member(
            chat_id, user_id, message.from_user.first_name,
        )

        other_member = await repo.get_other_member_in_chat(chat_id, sender_member_id)

        to_member_id = _resolve_recipient_member(
            sender_member_id, other_member, parsed.recipient_keyword,
        )

        if to_member_id is None and parsed.recipient_keyword not in ("мне", "нам", "всем"):
            await message.answer("Не понял, кому напомнить. Зарегистрируйтесь через /reg Имя")
            return

        rid = await repo.create_reminder(
            chat_id=chat_id,
            from_member_id=sender_member_id,
            to_member_id=to_member_id,
            text=parsed.text,
            remind_at=parsed.remind_at,
        )
        await session.commit()
        logger.info(
            "Reminder #%d created: remind_at=%s UTC, text='%s'",
            rid, parsed.remind_at.isoformat(), parsed.text,
        )

    time_str = _format_utc_to_local(parsed.remind_at, tz_offset_minutes)
    target = "тебе" if to_member_id == sender_member_id else (
        other_member.display_name if other_member and to_member_id == other_member.id else "всем"
    )
    await message.answer(
        f"Напоминание #{rid} создано!\n"
        f"📝 {parsed.text}\n"
        f"⏰ {time_str}\n"
        f"👤 Напомню {target}"
    )
