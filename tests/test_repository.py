import datetime

import pytest

from db.models import Chat, ChatMember, Reminder, ReminderStatus, User
from db.repository import Repository


@pytest.fixture
def repo(db_session):
    return Repository(db_session)


async def _create_chat_with_two_members(session) -> tuple[int, int, int, int]:
    chat = Chat(telegram_chat_id=-1001234567890)
    session.add(chat)
    await session.flush()

    user1 = User(telegram_id=111, full_name="Антон")
    user2 = User(telegram_id=222, full_name="Маша")
    session.add_all([user1, user2])
    await session.flush()

    member1 = ChatMember(chat_id=chat.id, user_id=user1.id, display_name="Антон")
    member2 = ChatMember(chat_id=chat.id, user_id=user2.id, display_name="Маша")
    session.add_all([member1, member2])
    await session.flush()

    return chat.id, member1.id, member2.id, user2.id


@pytest.mark.asyncio
async def test_get_or_create_chat_creates_new(db_session, repo):
    chat_id = await repo.get_or_create_chat(telegram_chat_id=-100999)
    assert chat_id is not None

    chat_id2 = await repo.get_or_create_chat(telegram_chat_id=-100999)
    assert chat_id2 == chat_id


@pytest.mark.asyncio
async def test_get_or_create_user_creates_new(db_session, repo):
    user_id = await repo.get_or_create_user(telegram_id=111, full_name="Антон")
    assert user_id is not None

    user_id2 = await repo.get_or_create_user(telegram_id=111, full_name="Антон Иванов")
    assert user_id2 == user_id


@pytest.mark.asyncio
async def test_register_member(db_session, repo):
    chat_id = await repo.get_or_create_chat(-1001)
    user_id = await repo.get_or_create_user(111, "Антон")
    member_id = await repo.register_member(chat_id, user_id, "Антон")
    assert member_id is not None


@pytest.mark.asyncio
async def test_register_member_updates_name(db_session, repo):
    chat_id = await repo.get_or_create_chat(-1001)
    user_id = await repo.get_or_create_user(111, "Антон")
    member_id1 = await repo.register_member(chat_id, user_id, "Антон")
    member_id2 = await repo.register_member(chat_id, user_id, "Тоха")
    assert member_id1 == member_id2

    member = await repo.get_member_by_telegram_id(-1001, 111)
    assert member.display_name == "Тоха"


@pytest.mark.asyncio
async def test_get_member_by_telegram_id(db_session, repo):
    chat_id = await repo.get_or_create_chat(-1001)
    user_id = await repo.get_or_create_user(111, "Антон")
    await repo.register_member(chat_id, user_id, "Антон")

    member = await repo.get_member_by_telegram_id(-1001, 111)
    assert member is not None
    assert member.display_name == "Антон"


@pytest.mark.asyncio
async def test_get_member_by_telegram_id_not_found(db_session, repo):
    member = await repo.get_member_by_telegram_id(999, 999)
    assert member is None


@pytest.mark.asyncio
async def test_create_reminder(db_session, repo):
    chat_id, m1_id, m2_id, _ = await _create_chat_with_two_members(db_session)
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    rid = await repo.create_reminder(
        chat_id=chat_id,
        from_member_id=m1_id,
        to_member_id=m2_id,
        text="купить хлеб",
        remind_at=now,
    )
    assert rid is not None


@pytest.mark.asyncio
async def test_get_active_reminders(db_session, repo):
    chat_id, m1_id, m2_id, _ = await _create_chat_with_two_members(db_session)
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    await repo.create_reminder(chat_id, m1_id, m2_id, "купить хлеб", now)

    reminders = await repo.get_active_reminders_for_member(m2_id)
    assert len(reminders) == 1
    assert reminders[0].text == "купить хлеб"


@pytest.mark.asyncio
async def test_get_incoming_reminders(db_session, repo):
    chat_id, m1_id, m2_id, _ = await _create_chat_with_two_members(db_session)
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    await repo.create_reminder(chat_id, m1_id, m2_id, "позвонить", now)

    reminders = await repo.get_incoming_reminders(m2_id)
    assert len(reminders) == 1
    assert reminders[0].from_member_id == m1_id


@pytest.mark.asyncio
async def test_cancel_reminder(db_session, repo):
    chat_id, m1_id, m2_id, _ = await _create_chat_with_two_members(db_session)
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    rid = await repo.create_reminder(chat_id, m1_id, m2_id, "тест", now)

    ok = await repo.cancel_reminder(rid, m1_id)
    assert ok is True

    reminders = await repo.get_active_reminders_for_member(m2_id)
    assert len(reminders) == 0


@pytest.mark.asyncio
async def test_cancel_reminder_not_owner(db_session, repo):
    chat_id, m1_id, m2_id, _ = await _create_chat_with_two_members(db_session)
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    rid = await repo.create_reminder(chat_id, m1_id, m2_id, "тест", now)

    ok = await repo.cancel_reminder(rid, 9999)
    assert ok is False


@pytest.mark.asyncio
async def test_mark_done(db_session, repo):
    chat_id, m1_id, m2_id, _ = await _create_chat_with_two_members(db_session)
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    rid = await repo.create_reminder(chat_id, m1_id, m2_id, "тест", now)

    ok = await repo.mark_done(rid, m2_id)
    assert ok is True


@pytest.mark.asyncio
async def test_snooze_reminder(db_session, repo):
    chat_id, m1_id, m2_id, _ = await _create_chat_with_two_members(db_session)
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    rid = await repo.create_reminder(chat_id, m1_id, m2_id, "тест", now)

    snooze_until = now + datetime.timedelta(minutes=10)
    ok = await repo.snooze_reminder(rid, snooze_until)
    assert ok is True


@pytest.mark.asyncio
async def test_get_overdue_reminders(db_session, repo):
    chat_id, m1_id, m2_id, _ = await _create_chat_with_two_members(db_session)
    past = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(minutes=5)
    await repo.create_reminder(chat_id, m1_id, m2_id, "просрочено", past)

    overdue = await repo.get_overdue_reminders()
    assert len(overdue) == 1
    assert overdue[0].text == "просрочено"


@pytest.mark.asyncio
async def test_get_overdue_skips_snoozed_not_ready(db_session, repo):
    chat_id, m1_id, m2_id, _ = await _create_chat_with_two_members(db_session)
    past = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(minutes=5)
    rid = await repo.create_reminder(chat_id, m1_id, m2_id, "отложено", past)

    future = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(minutes=10)
    await repo.snooze_reminder(rid, future)

    overdue = await repo.get_overdue_reminders()
    assert len(overdue) == 0


@pytest.mark.asyncio
async def test_set_quiet_until(db_session, repo):
    chat_id = await repo.get_or_create_chat(-1001)
    user_id = await repo.get_or_create_user(111, "Антон")
    member_id = await repo.register_member(chat_id, user_id, "Антон")

    quiet_until = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(hours=2)
    await repo.set_quiet_until(member_id, quiet_until)

    member = await repo.get_member_by_telegram_id(-1001, 111)
    assert member.quiet_until is not None


@pytest.mark.asyncio
async def test_get_other_member_in_chat(db_session, repo):
    chat_id, m1_id, m2_id, _ = await _create_chat_with_two_members(db_session)

    other = await repo.get_other_member_in_chat(chat_id, m1_id)
    assert other is not None
    assert other.id == m2_id


@pytest.mark.asyncio
async def test_set_chat_tz(db_session, repo):
    chat_id = await repo.get_or_create_chat(-1001)
    await repo.set_chat_tz(chat_id, 330)  # UTC+5:30
    await db_session.commit()

    chat = await repo.get_chat_by_telegram_id(-1001)
    assert chat.tz_offset_minutes == 330


@pytest.mark.asyncio
async def test_chat_default_tz_offset(db_session, repo):
    chat_id = await repo.get_or_create_chat(-1001)
    chat = await repo.get_chat_by_telegram_id(-1001)
    assert chat.tz_offset_minutes == 180  # default UTC+3
