import datetime
import re

from aiogram import Router, types
from aiogram.filters import Command
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from db.models import Reminder, ReminderStatus
from db.repository import Repository


def _format_utc_to_local(utc_dt: datetime.datetime, tz_offset_minutes: int) -> str:
    tz = datetime.timezone(datetime.timedelta(minutes=tz_offset_minutes))
    local_dt = utc_dt.astimezone(tz)
    return local_dt.strftime("%H:%M")

router = Router()

QUIET_PATTERN = re.compile(r"(\d+)\s*(мин|час|ч|м)", re.IGNORECASE)

TZ_PATTERN = re.compile(r"^([+-]?\d{1,2})(?::?(\d{2}))?$")


@router.message(Command("tz"))
async def cmd_tz(message: types.Message) -> None:
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Напиши: /tz 3\nНапример: /tz 3 (Москва), /tz -5 (Нью-Йорк), /tz 5:30")
        return

    match = TZ_PATTERN.match(parts[1].strip())
    if not match:
        await message.answer("Не понял часовой пояс. Примеры: /tz 3, /tz -5, /tz 5:30")
        return

    hours = int(match.group(1))
    minutes = int(match.group(2)) if match.group(2) else 0
    if not (-12 <= hours <= 14) or not (0 <= minutes <= 59):
        await message.answer("Часовой пояс должен быть от -12 до +14.")
        return

    tz_offset_minutes = hours * 60 + (minutes if hours >= 0 else -minutes)

    session_factory: async_sessionmaker = message.bot.session_factory

    async with session_factory() as session:
        repo = Repository(session)
        chat_id = await repo.get_or_create_chat(message.chat.id)
        await repo.set_chat_tz(chat_id, tz_offset_minutes)
        await session.commit()

    sign = "+" if hours >= 0 else ""
    if minutes:
        await message.answer(f"🌍 Часовой пояс установлен: UTC{sign}{hours}:{minutes:02d}")
    else:
        await message.answer(f"🌍 Часовой пояс установлен: UTC{sign}{hours}")


@router.message(Command("quiet"))
async def cmd_quiet(message: types.Message) -> None:
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Напиши: /quiet 2ч\nНапример: /quiet 30мин, /quiet 2ч")
        return

    match = QUIET_PATTERN.search(parts[1])
    if not match:
        await message.answer("Не понял время. Примеры: /quiet 30мин, /quiet 2ч")
        return

    amount = int(match.group(1))
    unit = match.group(2).lower()

    if unit.startswith("ч"):
        delta = datetime.timedelta(hours=amount)
    else:
        delta = datetime.timedelta(minutes=amount)

    quiet_until = datetime.datetime.now(tz=datetime.timezone.utc) + delta
    session_factory: async_sessionmaker = message.bot.session_factory

    async with session_factory() as session:
        repo = Repository(session)
        member = await repo.get_member_by_telegram_id(
            message.chat.id, message.from_user.id,
        )
        if not member:
            await message.answer("Ты ещё не зарегистрирован. Напиши: /reg Имя")
            return

        await repo.set_quiet_until(member.id, quiet_until)
        chat = await repo.get_chat_by_telegram_id(message.chat.id)
        await session.commit()

    tz_offset_minutes = chat.tz_offset_minutes if chat else 180
    local_time = _format_utc_to_local(quiet_until, tz_offset_minutes)
    await message.answer(f"🔇 Тихий режим до {local_time} ({amount} {match.group(2)})")


@router.message(Command("stats"))
async def cmd_stats(message: types.Message) -> None:
    session_factory: async_sessionmaker = message.bot.session_factory

    async with session_factory() as session:
        repo = Repository(session)
        member = await repo.get_member_by_telegram_id(
            message.chat.id, message.from_user.id,
        )
        if not member:
            await message.answer("Ты ещё не зарегистрирован. Напиши: /reg Имя")
            return

        week_ago = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=7)

        created_count = await session.scalar(
            select(func.count()).select_from(Reminder).where(
                Reminder.from_member_id == member.id,
                Reminder.created_at >= week_ago,
            )
        )
        done_count = await session.scalar(
            select(func.count()).select_from(Reminder).where(
                Reminder.to_member_id == member.id,
                Reminder.status == ReminderStatus.DONE,
                Reminder.created_at >= week_ago,
            )
        )
        await session.commit()

    await message.answer(
        f"📊 Статистика за 7 дней:\n\n"
        f"📝 Создано напоминаний: {created_count}\n"
        f"✔️ Выполнено: {done_count}"
    )


@router.message(Command("help"))
async def cmd_help(message: types.Message) -> None:
    await message.answer(
        "🧠 <b>А голову не забыл?</b>\n\n"
        "Просто пиши в чат:\n"
        "• «напомни мне через 30 мин позвонить»\n"
        "• «напомни ей завтра в 9:00 купить хлеб»\n"
        "• «через час выключить духовку»\n\n"
        "<b>Команды:</b>\n"
        "/reg Имя — представиться\n"
        "/my — мои напоминания\n"
        "/our — от партнёра\n"
        "/del ID — удалить\n"
        "/tz 3 — часовой пояс (UTC)\n"
        "/quiet 2ч — не беспокоить\n"
        "/who — кто я\n"
        "/stats — за 7 дней\n"
        "/faq — частые вопросы\n"
        "/help — эта справка"
    )


@router.message(Command("faq"))
async def cmd_faq(message: types.Message) -> None:
    from bot.content import FAQ, get_faq_keyboard

    if not FAQ:
        await message.answer("FAQ пока пуст.")
        return

    await message.answer("❓ Частые вопросы:", reply_markup=get_faq_keyboard())
