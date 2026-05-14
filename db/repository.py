import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Chat, ChatMember, Reminder, ReminderStatus, User


class Repository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_chat(self, telegram_chat_id: int) -> int:
        stmt = select(Chat).where(Chat.telegram_chat_id == telegram_chat_id)
        result = await self.session.execute(stmt)
        chat = result.scalar_one_or_none()
        if chat:
            return chat.id
        chat = Chat(telegram_chat_id=telegram_chat_id)
        self.session.add(chat)
        await self.session.flush()
        return chat.id

    async def get_chat_by_telegram_id(self, telegram_chat_id: int) -> Chat | None:
        stmt = select(Chat).where(Chat.telegram_chat_id == telegram_chat_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def set_chat_tz(self, chat_id: int, tz_offset_minutes: int) -> None:
        chat = await self.session.get(Chat, chat_id)
        if chat:
            chat.tz_offset_minutes = tz_offset_minutes
            await self.session.flush()

    async def get_or_create_user(self, telegram_id: int, full_name: str) -> int:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            user.full_name = full_name
            await self.session.flush()
            return user.id
        user = User(telegram_id=telegram_id, full_name=full_name)
        self.session.add(user)
        await self.session.flush()
        return user.id

    async def register_member(self, chat_id: int, user_id: int, display_name: str) -> int:
        stmt = select(ChatMember).where(
            ChatMember.chat_id == chat_id,
            ChatMember.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        member = result.scalar_one_or_none()
        if member:
            member.display_name = display_name
            await self.session.flush()
            return member.id
        member = ChatMember(chat_id=chat_id, user_id=user_id, display_name=display_name)
        self.session.add(member)
        await self.session.flush()
        return member.id

    async def get_member_by_telegram_id(
        self, telegram_chat_id: int, telegram_user_id: int,
    ) -> ChatMember | None:
        stmt = (
            select(ChatMember)
            .join(User)
            .join(Chat, ChatMember.chat_id == Chat.id)
            .where(
                Chat.telegram_chat_id == telegram_chat_id,
                User.telegram_id == telegram_user_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_other_member_in_chat(
        self, chat_id: int, member_id: int,
    ) -> ChatMember | None:
        stmt = (
            select(ChatMember)
            .where(ChatMember.chat_id == chat_id, ChatMember.id != member_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_reminder(
        self,
        chat_id: int,
        from_member_id: int,
        to_member_id: int | None,
        text: str,
        remind_at: datetime.datetime,
    ) -> int:
        reminder = Reminder(
            chat_id=chat_id,
            from_member_id=from_member_id,
            to_member_id=to_member_id,
            text=text,
            remind_at=remind_at,
        )
        self.session.add(reminder)
        await self.session.flush()
        return reminder.id

    async def get_active_reminders_for_member(
        self, member_id: int,
    ) -> list[Reminder]:
        stmt = (
            select(Reminder)
            .where(
                Reminder.to_member_id == member_id,
                Reminder.status == ReminderStatus.ACTIVE,
            )
            .order_by(Reminder.remind_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_incoming_reminders(self, member_id: int) -> list[Reminder]:
        stmt = (
            select(Reminder)
            .where(
                Reminder.to_member_id == member_id,
                Reminder.from_member_id != member_id,
                Reminder.status == ReminderStatus.ACTIVE,
            )
            .order_by(Reminder.remind_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def cancel_reminder(self, reminder_id: int, caller_member_id: int) -> bool:
        stmt = select(Reminder).where(
            Reminder.id == reminder_id,
            Reminder.status == ReminderStatus.ACTIVE,
        )
        result = await self.session.execute(stmt)
        reminder = result.scalar_one_or_none()
        if not reminder:
            return False
        if reminder.from_member_id != caller_member_id and reminder.to_member_id != caller_member_id:
            return False
        reminder.status = ReminderStatus.CANCELLED
        await self.session.flush()
        return True

    async def mark_done(self, reminder_id: int, caller_member_id: int) -> bool:
        stmt = select(Reminder).where(
            Reminder.id == reminder_id,
            Reminder.status.in_([ReminderStatus.ACTIVE, ReminderStatus.SNOOZED, ReminderStatus.DELIVERED]),
        )
        result = await self.session.execute(stmt)
        reminder = result.scalar_one_or_none()
        if not reminder:
            return False
        if reminder.to_member_id != caller_member_id:
            return False
        reminder.status = ReminderStatus.DONE
        await self.session.flush()
        return True

    async def snooze_reminder(
        self, reminder_id: int, snoozed_until: datetime.datetime,
    ) -> bool:
        stmt = select(Reminder).where(Reminder.id == reminder_id)
        result = await self.session.execute(stmt)
        reminder = result.scalar_one_or_none()
        if not reminder:
            return False
        reminder.status = ReminderStatus.SNOOZED
        reminder.snoozed_until = snoozed_until
        await self.session.flush()
        return True

    async def get_overdue_reminders(self) -> list[Reminder]:
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        stmt = (
            select(Reminder)
            .where(
                Reminder.status == ReminderStatus.ACTIVE,
                Reminder.remind_at <= now,
            )
        )
        result = await self.session.execute(stmt)
        active_overdue = list(result.scalars().all())

        snoozed_stmt = (
            select(Reminder)
            .where(
                Reminder.status == ReminderStatus.SNOOZED,
                Reminder.snoozed_until <= now,
            )
        )
        result2 = await self.session.execute(snoozed_stmt)
        snoozed_overdue = list(result2.scalars().all())

        return active_overdue + snoozed_overdue

    async def set_quiet_until(
        self, member_id: int, quiet_until: datetime.datetime | None,
    ) -> None:
        stmt = select(ChatMember).where(ChatMember.id == member_id)
        result = await self.session.execute(stmt)
        member = result.scalar_one_or_none()
        if member:
            member.quiet_until = quiet_until
            await self.session.flush()
