import datetime

from db.models import Chat, User, ChatMember, Reminder, ReminderStatus


def test_chat_model():
    chat = Chat(telegram_chat_id=-1001234567890)
    assert chat.telegram_chat_id == -1001234567890
    assert chat.id is None


def test_user_model():
    user = User(telegram_id=123456789, full_name="Антон")
    assert user.telegram_id == 123456789
    assert user.full_name == "Антон"


def test_chat_member_model():
    member = ChatMember(
        chat_id=1,
        user_id=1,
        display_name="Антон",
    )
    assert member.display_name == "Антон"
    assert member.quiet_until is None


def test_reminder_model():
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    reminder = Reminder(
        chat_id=1,
        from_member_id=1,
        to_member_id=2,
        text="позвонить в банк",
        remind_at=now,
    )
    assert reminder.status == ReminderStatus.ACTIVE
    assert reminder.text == "позвонить в банк"
    assert reminder.snoozed_until is None


def test_reminder_to_member_nullable():
    reminder = Reminder(
        chat_id=1,
        from_member_id=1,
        to_member_id=None,
        text="купить хлеб",
        remind_at=datetime.datetime.now(tz=datetime.timezone.utc),
    )
    assert reminder.to_member_id is None


def test_reminder_status_enum():
    assert ReminderStatus.ACTIVE.value == "active"
    assert ReminderStatus.DONE.value == "done"
    assert ReminderStatus.SNOOZED.value == "snoozed"
    assert ReminderStatus.CANCELLED.value == "cancelled"
