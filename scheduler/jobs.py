import datetime
import logging

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from db.models import Chat, ChatMember, Reminder, ReminderStatus
from db.repository import Repository

logger = logging.getLogger(__name__)


async def check_and_send_reminders(
    session_factory: async_sessionmaker, bot: Bot,
) -> None:
    try:
        async with session_factory() as session:
            repo = Repository(session)
            overdue = await repo.get_overdue_reminders()
            now = datetime.datetime.now(tz=datetime.timezone.utc)
            logger.info(
                "Scheduler tick: now=%s UTC, found %d overdue reminders",
                now.isoformat(), len(overdue),
            )

            for reminder in overdue:
                logger.info(
                    "Processing reminder #%d: remind_at=%s, status=%s, chat_id=%s",
                    reminder.id, reminder.remind_at.isoformat(),
                    reminder.status.value, reminder.chat_id,
                )
                await _send_notification(session, bot, reminder)

            await session.commit()
    except Exception:
        logger.exception("Scheduler tick failed")


async def _send_notification(session, bot: Bot, reminder: Reminder) -> None:
    from bot.handlers.callbacks import get_reminder_keyboard

    chat_obj = await session.get(Chat, reminder.chat_id)
    if not chat_obj:
        return

    if reminder.to_member_id:
        to_member = await session.get(ChatMember, reminder.to_member_id)
        if not to_member:
            return

        if to_member.quiet_until:
            now = datetime.datetime.now(tz=datetime.timezone.utc)
            if to_member.quiet_until > now:
                logger.info(
                    f"Skipping reminder #{reminder.id}: quiet mode for member {to_member.id}",
                )
                return

        name = to_member.display_name
    else:
        name = "Всем"

    from_member = await session.get(ChatMember, reminder.from_member_id)
    from_name = from_member.display_name if from_member else "Кто-то"

    keyboard = get_reminder_keyboard(reminder.id)

    try:
        await bot.send_message(
            chat_id=chat_obj.telegram_chat_id,
            text=(
                f"🧠 А голову не забыл?\n"
                f"{name}, 🔔 {from_name.upper()} ПРОСИЛ(А) НАПОМНИТЬ: {reminder.text}"
            ),
            reply_markup=keyboard,
        )
        reminder.status = ReminderStatus.DELIVERED
        reminder.snoozed_until = None
        await session.flush()
        logger.info(f"Sent reminder #{reminder.id}")

    except Exception as e:
        logger.error(f"Failed to send reminder #{reminder.id}: {e}")
