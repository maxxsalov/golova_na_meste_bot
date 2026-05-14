from __future__ import annotations

import datetime
import logging
import re
from dataclasses import dataclass

import dateparser

logger = logging.getLogger(__name__)

TRIGGER_WORDS = re.compile(
    r"\b(напомни|напомнить)\b"
    r"|\bчерез\s+(\d+\s*)?(минут|мин|час|часа|часов|день|дня|дней)"
    r"|\bчерез\s+\d+"
    r"|\b(завтра|сегодня|послезавтра)\s+в\s+\d",
    re.IGNORECASE,
)

_DELTA_PATTERN = re.compile(
    r"через\s+(\d+)\s*(минут|мин|час|часа|часов|день|дня|дней)?",
    re.IGNORECASE,
)

_ABSOLUTE_TIME_PATTERN = re.compile(
    r"(завтра|сегодня|послезавтра)\s+в\s+(\d{1,2}):(\d{2})",
    re.IGNORECASE,
)

_UNIT_MINUTES = {"минут", "мин"}
_UNIT_HOURS = {"час", "часа", "часов"}
_UNIT_DAYS = {"день", "дня", "дней"}

RECIPIENT_PATTERN = re.compile(
    r"\b(мне|нам|ей|ему|всем)\b",
    re.IGNORECASE,
)

RECIPIENT_NAME_HINTS = re.compile(
    r"\bнапомни\s+([А-ЯЁA-Z][а-яёa-z]+(?:у|е|ю|ой|ам|ем|ом|аш|ишь|ешь))\b",
    re.IGNORECASE,
)

STRIP_PATTERN = re.compile(
    r"\bнапомни(?:ть)?\b"
    r"|\b(?:мне|нам|ей|ему|всем)\b"
    r"|\bчерез\s+\d+\s*(?:минут[а-яё]*|мин\b|час[а-яё]*|день|дня|дней)?\b"
    r"|\b(?:завтра|сегодня|послезавтра)\s+в\s+\d{1,2}:\d{2}\b"
    r"|\bв\s+\d{1,2}:\d{2}\b",
    re.IGNORECASE,
)

DEFAULT_REMIND_DELTA = datetime.timedelta(minutes=30)


def _make_tz(offset_minutes: int) -> datetime.timezone:
    return datetime.timezone(datetime.timedelta(minutes=offset_minutes))


@dataclass
class ParseResult:
    recipient_keyword: str
    remind_at: datetime.datetime
    text: str
    raw: str


def _extract_text(message: str) -> str:
    cleaned = STRIP_PATTERN.sub("", message)
    return " ".join(cleaned.split()).strip()


def _extract_time(message: str, tz_offset_minutes: int = 180) -> datetime.datetime:
    tz = _make_tz(tz_offset_minutes)
    now = datetime.datetime.now(tz=tz)

    # Direct regex for "через N [unit]" patterns
    delta = _parse_delta(message)
    if delta is not None:
        return (now + delta).astimezone(datetime.timezone.utc)

    # Direct regex for "завтра/сегодня/послезавтра в HH:MM"
    abs_time = _parse_absolute_time(message, tz)
    if abs_time is not None:
        return abs_time.astimezone(datetime.timezone.utc)

    # Fallback to dateparser
    sign = "+" if tz_offset_minutes >= 0 else "-"
    total = abs(tz_offset_minutes)
    tz_str = f"{sign}{total // 60:02d}{total % 60:02d}"
    parsed = dateparser.parse(
        message,
        languages=["ru"],
        settings={
            "PREFER_DATES_FROM": "future",
            "TIMEZONE": tz_str,
            "RETURN_AS_TIMEZONE_AWARE": True,
        },
    )
    if parsed:
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=tz)
        logger.debug("dateparser parsed '%s' → %s", message, parsed.isoformat())
        return parsed.astimezone(datetime.timezone.utc)

    logger.warning("dateparser failed for '%s', defaulting to +30min", message)
    return (now + DEFAULT_REMIND_DELTA).astimezone(datetime.timezone.utc)


def _parse_delta(message: str) -> datetime.timedelta | None:
    m = _DELTA_PATTERN.search(message)
    if not m:
        return None
    n = int(m.group(1))
    unit = (m.group(2) or "").lower()
    if unit in _UNIT_MINUTES:
        return datetime.timedelta(minutes=n)
    if unit in _UNIT_HOURS:
        return datetime.timedelta(hours=n)
    if unit in _UNIT_DAYS:
        return datetime.timedelta(days=n)
    # No unit — assume minutes
    return datetime.timedelta(minutes=n)


def _parse_absolute_time(
    message: str, tz: datetime.timezone,
) -> datetime.datetime | None:
    m = _ABSOLUTE_TIME_PATTERN.search(message)
    if not m:
        return None
    day_word = m.group(1).lower()
    hour = int(m.group(2))
    minute = int(m.group(3))

    now = datetime.datetime.now(tz=tz)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if day_word == "завтра":
        target += datetime.timedelta(days=1)
    elif day_word == "послезавтра":
        target += datetime.timedelta(days=2)

    if target <= now and day_word == "сегодня":
        target += datetime.timedelta(days=1)

    return target.replace(tzinfo=tz)


def parse_message(message: str, tz_offset_minutes: int = 180) -> ParseResult | None:
    if not TRIGGER_WORDS.search(message):
        return None

    recipient = _extract_recipient(message)
    remind_at = _extract_time(message, tz_offset_minutes=tz_offset_minutes)
    text = _extract_text(message)

    if not text:
        return None

    return ParseResult(
        recipient_keyword=recipient,
        remind_at=remind_at,
        text=text,
        raw=message,
    )


def _extract_recipient(message: str) -> str:
    pronoun_match = RECIPIENT_PATTERN.search(message)
    if pronoun_match:
        return pronoun_match.group(1).lower()

    name_match = RECIPIENT_NAME_HINTS.search(message)
    if name_match:
        return name_match.group(1)

    return "мне"
