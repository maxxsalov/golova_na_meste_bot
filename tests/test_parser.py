import datetime

import pytest

from bot.parser import parse_message, ParseResult


def test_parse_recipient_me():
    result = parse_message("напомни мне через 30 мин позвонить")
    assert result.recipient_keyword == "мне"


def test_parse_recipient_her():
    result = parse_message("напомни ей завтра в 9:00 купить хлеб")
    assert result.recipient_keyword == "ей"


def test_parse_recipient_him():
    result = parse_message("напомни ему позвонить в банк")
    assert result.recipient_keyword == "ему"


def test_parse_recipient_name():
    result = parse_message("напомни Антону позвонить")
    assert result.recipient_keyword == "Антону"


def test_parse_recipient_default_when_absent():
    result = parse_message("через час выключить духовку")
    assert result.recipient_keyword == "мне"


def test_parse_recipient_default_with_napomni_only():
    result = parse_message("напомни купить хлеб")
    assert result.recipient_keyword == "мне"


def test_parse_no_trigger_word_returns_none():
    result = parse_message("привет как дела")
    assert result is None


def test_parse_recipient_us():
    result = parse_message("напомни нам сходить в магазин")
    assert result.recipient_keyword == "нам"


def test_parse_recipient_everyone():
    result = parse_message("напомни всем собраться")
    assert result.recipient_keyword == "всем"


def test_parse_time_relative_minutes():
    result = parse_message("напомни мне через 30 мин позвонить")
    assert result is not None
    assert result.remind_at is not None


def test_parse_time_relative_hours():
    result = parse_message("через 2 часа выключить духовку")
    assert result is not None
    assert result.remind_at is not None


def test_parse_time_absolute():
    result = parse_message("напомни мне завтра в 9:00 купить хлеб")
    assert result is not None
    assert result.remind_at is not None


def test_parse_time_default_when_absent():
    result = parse_message("напомни мне купить хлеб")
    assert result is not None
    assert result.remind_at is not None
    # default = now + 30 min
    import datetime
    delta = result.remind_at - datetime.datetime.now(tz=datetime.timezone.utc)
    assert 25 * 60 < delta.total_seconds() < 35 * 60


def test_parse_time_today_absolute():
    result = parse_message("напомни в 19:00 позвонить")
    assert result is not None
    assert result.remind_at is not None


def test_parse_text_extracts_reminder_body():
    result = parse_message("напомни мне через 30 мин позвонить в банк")
    assert result is not None
    assert "позвонить в банк" in result.text
    assert "напомни" not in result.text.lower()
    assert "через 30 мин" not in result.text.lower()


def test_parse_text_simple():
    result = parse_message("через час выключить духовку")
    assert result is not None
    assert "выключить духовку" in result.text


def test_parse_text_absolute_time():
    result = parse_message("напомни ей завтра в 9:00 купить хлеб")
    assert result is not None
    assert "купить хлеб" in result.text


def test_parse_full_pipeline():
    result = parse_message("напомни мне через 30 мин позвонить")
    assert result is not None
    assert result.recipient_keyword == "мне"
    assert result.remind_at is not None
    assert "позвонить" in result.text


def test_parse_with_custom_tz_offset():
    result = parse_message("напомни мне через 30 мин позвонить", tz_offset_minutes=330)
    assert result is not None
    assert result.remind_at is not None


def test_parse_with_negative_tz_offset():
    result = parse_message("напомни мне через 1 час позвонить", tz_offset_minutes=-300)
    assert result is not None
    assert result.remind_at is not None


def test_format_utc_to_local_positive():
    from bot.handlers.reminders import _format_utc_to_local
    utc_dt = datetime.datetime(2026, 1, 15, 12, 0, tzinfo=datetime.timezone.utc)
    assert _format_utc_to_local(utc_dt, 180) == "15:00 15.01"  # UTC+3


def test_format_utc_to_local_negative():
    from bot.handlers.reminders import _format_utc_to_local
    utc_dt = datetime.datetime(2026, 1, 15, 12, 0, tzinfo=datetime.timezone.utc)
    assert _format_utc_to_local(utc_dt, -300) == "07:00 15.01"  # UTC-5


def test_format_utc_to_local_fractional():
    from bot.handlers.reminders import _format_utc_to_local
    utc_dt = datetime.datetime(2026, 1, 15, 12, 0, tzinfo=datetime.timezone.utc)
    assert _format_utc_to_local(utc_dt, 330) == "17:30 15.01"  # UTC+5:30


def test_tz_pattern_valid():
    from bot.handlers.misc import TZ_PATTERN
    assert TZ_PATTERN.match("3") is not None
    assert TZ_PATTERN.match("-5") is not None
    assert TZ_PATTERN.match("+5:30") is not None
    assert TZ_PATTERN.match("530") is not None


def test_tz_pattern_invalid():
    from bot.handlers.misc import TZ_PATTERN
    assert TZ_PATTERN.match("abc") is None
    assert TZ_PATTERN.match("") is None
    assert TZ_PATTERN.match("3:5") is None  # single digit minutes
    assert TZ_PATTERN.match("3:") is None
