from __future__ import annotations

import re

from aiogram import types

CYRILLIC_RE = re.compile(r"[а-яёА-ЯЁ]")


FAQ: list[dict[str, str]] = [
    {
        "q": "Как создать напоминание?",
        "a": (
            "Просто напиши в чат:\n"
            "• «напомни мне через 30 мин позвонить»\n"
            "• «напомни ей завтра в 9:00 купить хлеб»\n"
            "• «через час выключить духовку»\n\n"
            "Бот сам поймёт, когда напомнить."
        ),
    },
    {
        "q": "Как изменить часовой пояс?",
        "a": (
            "Напиши <b>/tz 3</b> для Москвы (UTC+3).\n"
            "Примеры:\n"
            "• /tz -5 — Нью-Йорк\n"
            "• /tz 5:30 — Индия\n"
            "• /tz 6 — Дакка"
        ),
    },
    {
        "q": "Как удалить напоминание?",
        "a": (
            "Напиши <b>/del ID</b> — номер видно в списке напоминаний.\n"
            "Пример: /del 42\n\n"
            "Список ID: /my — твои, /our — от партнёра."
        ),
    },
    {
        "q": "Как работает тихий режим?",
        "a": (
            "Команда <b>/quiet</b> выключает уведомления на указанное время.\n"
            "Примеры:\n"
            "• /quiet 30мин\n"
            "• /quiet 2ч\n\n"
            "Напоминания не теряются — бот отправит их после выхода из тихого режима."
        ),
    },
    {
        "q": "Кому бот может напомнить?",
        "a": (
            "Бот понимает:\n"
            "• «напомни <b>мне</b>» — тебе\n"
            "• «напомни <b>ей</b>» / «напомни <b>ему</b>» — партнёру\n"
            "• «напомни <b>всем</b>» / «напомни <b>нам</b>» — обоим\n\n"
            "Для этого оба участника должны зарегистрироваться через /reg."
        ),
    },
    {
        "q": "Бот не реагирует на сообщения — почему?",
        "a": (
            "Бот реагирует только на:\n"
            "• Сообщения со словами «напомни», «через N минут/час», «завтра в HH:MM»\n"
            "• Команды (/reg, /my, /del и т.д.)\n\n"
            "Обычные сообщения бот игнорирует."
        ),
    },
]

INLINE_ITEMS: list[dict[str, str]] = [
    {"title": "/reg Имя", "description": "Представиться в чате", "text": "/reg "},
    {"title": "/my", "description": "Мои напоминания", "text": "/my"},
    {"title": "/our", "description": "Напоминания от партнёра", "text": "/our"},
    {"title": "/del ID", "description": "Удалить напоминание", "text": "/del "},
    {"title": "/tz 3", "description": "Часовой пояс (UTC+3)", "text": "/tz "},
    {"title": "/quiet 2ч", "description": "Не беспокоить 2 часа", "text": "/quiet "},
    {"title": "/who", "description": "Как меня зовёт бот", "text": "/who"},
    {"title": "/stats", "description": "Статистика за 7 дней", "text": "/stats"},
    {"title": "/help", "description": "Справка по командам", "text": "/help"},
    {"title": "/faq", "description": "Частые вопросы", "text": "/faq"},
]

RUSSIAN_COMMAND_MAP: dict[str, str] = {
    "регистрация": "reg",
    "рег": "reg",
    "мои": "my",
    "мои_напоминания": "my",
    "наши": "our",
    "наши_напоминания": "our",
    "удалить": "del",
    "удал": "del",
    "помощь": "help",
    "помоги": "help",
    "тихий": "quiet",
    "тишина": "quiet",
    "стат": "stats",
    "статистика": "stats",
    "часовой": "tz",
    "пояс": "tz",
    "кто": "who",
    "вопросы": "faq",
    "фак": "faq",
}


def match_russian_command(text: str) -> str | None:
    """Check if a /command is a Russian typo and return the correct Latin command."""
    if not text.startswith("/"):
        return None
    cmd = text[1:].lower().split("@")[0].strip()
    if not cmd:
        return None
    if not CYRILLIC_RE.search(cmd):
        return None
    for ru_key, en_cmd in RUSSIAN_COMMAND_MAP.items():
        if cmd.startswith(ru_key):
            return f"/{en_cmd}"
    return None


def filter_inline_items(query: str) -> list[dict[str, str]]:
    """Filter inline items by first word of user query."""
    if not query.strip():
        return list(INLINE_ITEMS)
    q = query.lower().strip().lstrip("/").split()[0]
    if not q:
        return list(INLINE_ITEMS)
    matched = [
        item
        for item in INLINE_ITEMS
        if q in item["title"].lower() or q in item["description"].lower()
    ]
    return matched if matched else list(INLINE_ITEMS)


def get_faq_keyboard() -> types.InlineKeyboardMarkup:
    """Build inline keyboard with FAQ question buttons."""
    buttons = [
        [
            types.InlineKeyboardButton(
                text=item["q"],
                callback_data=f"faq:{i}",
            )
        ]
        for i, item in enumerate(FAQ)
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)
