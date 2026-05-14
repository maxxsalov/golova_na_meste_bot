import datetime
import enum

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ReminderStatus(str, enum.Enum):
    ACTIVE = "active"
    DELIVERED = "delivered"
    DONE = "done"
    SNOOZED = "snoozed"
    CANCELLED = "cancelled"


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.timezone.utc)


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    tz_offset_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=180)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow,
    )

    members: Mapped[list["ChatMember"]] = relationship(back_populates="chat")
    reminders: Mapped[list["Reminder"]] = relationship(back_populates="chat")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow,
    )

    memberships: Mapped[list["ChatMember"]] = relationship(back_populates="user")


class ChatMember(Base):
    __tablename__ = "chats_members"
    __table_args__ = (
        UniqueConstraint("chat_id", "user_id", name="uq_chat_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(Integer, ForeignKey("chats.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    quiet_until: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow,
    )

    chat: Mapped["Chat"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="memberships")


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(Integer, ForeignKey("chats.id"), nullable=False)
    from_member_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chats_members.id"), nullable=False,
    )
    to_member_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("chats_members.id"), nullable=True,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    remind_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    status: Mapped[ReminderStatus] = mapped_column(
        Enum(ReminderStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False, default=ReminderStatus.ACTIVE,
    )
    snoozed_until: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow,
    )

    chat: Mapped["Chat"] = relationship(back_populates="reminders")
    from_member: Mapped["ChatMember"] = relationship(foreign_keys=[from_member_id])
    to_member: Mapped["ChatMember | None"] = relationship(foreign_keys=[to_member_id])

    def __init__(self, **kwargs):
        if 'status' not in kwargs:
            kwargs['status'] = ReminderStatus.ACTIVE
        super().__init__(**kwargs)
