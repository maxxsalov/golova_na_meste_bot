import datetime

from aiogram import Router, types
from aiogram.filters import callback_data
from sqlalchemy.ext.asyncio import async_sessionmaker

from db.repository import Repository


def _format_utc_to_local(utc_dt: datetime.datetime, tz_offset_minutes: int) -> str:
    tz = datetime.timezone(datetime.timedelta(minutes=tz_offset_minutes))
    local_dt = utc_dt.astimezone(tz)
    return local_dt.strftime("%H:%M")


class ReminderCallback(callback_data.CallbackData, prefix="rem"):
    action: str  # "done" or "snooze"
    reminder_id: int


router = Router()


def get_reminder_keyboard(reminder_id: int) -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="✔️ Сделано",
                    callback_data=ReminderCallback(
                        action="done", reminder_id=reminder_id,
                    ).pack(),
                ),
                types.InlineKeyboardButton(
                    text="⏰ Ещё через 10 мин",
                    callback_data=ReminderCallback(
                        action="snooze", reminder_id=reminder_id,
                    ).pack(),
                ),
            ],
        ],
    )


@router.callback_query(ReminderCallback.filter())
async def handle_reminder_callback(
    callback: types.CallbackQuery,
    callback_data: ReminderCallback,
) -> None:
    session_factory: async_sessionmaker = callback.bot.session_factory

    async with session_factory() as session:
        repo = Repository(session)
        member = await repo.get_member_by_telegram_id(
            callback.message.chat.id, callback.from_user.id,
        )
        if not member:
            await callback.answer("Ты не зарегистрирован.")
            return

        if callback_data.action == "done":
            ok = await repo.mark_done(callback_data.reminder_id, member.id)
            await session.commit()

            if ok:
                await callback.message.edit_text(
                    f"✔️ {member.display_name} выполнил(а) напоминание #{callback_data.reminder_id}",
                )
                await callback.answer("Отлично!")
            else:
                await callback.answer("Не удалось отметить как выполненное.")

        elif callback_data.action == "snooze":
            snooze_until = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(minutes=10)
            ok = await repo.snooze_reminder(callback_data.reminder_id, snooze_until)
            chat = await repo.get_chat_by_telegram_id(callback.message.chat.id)
            await session.commit()

            tz_offset_minutes = chat.tz_offset_minutes if chat else 180
            local_time = _format_utc_to_local(snooze_until, tz_offset_minutes)

            if ok:
                await callback.message.edit_text(
                    f"⏰ Напоминание #{callback_data.reminder_id} отложено до {local_time}",
                )
                await callback.answer("Отложено на 10 мин")
            else:
                await callback.answer("Не удалось отложить.")


@router.callback_query(lambda c: c.data and c.data.startswith("faq:"))
async def handle_faq_callback(callback: types.CallbackQuery) -> None:
    from bot.content import FAQ, get_faq_keyboard

    data = callback.data
    if data == "faq:back":
        await callback.message.edit_text(
            "❓ Частые вопросы:", reply_markup=get_faq_keyboard(),
        )
        await callback.answer()
        return

    try:
        index = int(data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("Ошибка.")
        return

    if index < 0 or index >= len(FAQ):
        await callback.answer("Статья не найдена.")
        return

    article = FAQ[index]
    back_button = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="← Назад", callback_data="faq:back")],
        ],
    )
    await callback.message.edit_text(
        f"❓ {article['q']}\n\n{article['a']}",
        reply_markup=back_button,
    )
    await callback.answer()
