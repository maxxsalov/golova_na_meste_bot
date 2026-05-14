from bot.content import FAQ, INLINE_ITEMS, RUSSIAN_COMMAND_MAP


def test_faq_is_list_with_q_and_a():
    assert isinstance(FAQ, list)
    assert len(FAQ) >= 6
    for item in FAQ:
        assert "q" in item
        assert "a" in item
        assert isinstance(item["q"], str)
        assert isinstance(item["a"], str)
        assert len(item["q"]) > 0
        assert len(item["a"]) > 0


def test_inline_items_is_list_with_required_fields():
    assert isinstance(INLINE_ITEMS, list)
    assert len(INLINE_ITEMS) >= 10
    for item in INLINE_ITEMS:
        assert "title" in item
        assert "description" in item
        assert "text" in item


def test_russian_command_map_is_dict():
    assert isinstance(RUSSIAN_COMMAND_MAP, dict)
    assert len(RUSSIAN_COMMAND_MAP) >= 5
    for ru, en in RUSSIAN_COMMAND_MAP.items():
        assert isinstance(ru, str)
        assert isinstance(en, str)
        assert en.startswith("/") is False


def test_russian_command_map_values_valid():
    valid_commands = {"reg", "my", "our", "del", "help", "quiet", "stats", "tz", "who", "faq"}
    for ru, en in RUSSIAN_COMMAND_MAP.items():
        assert en in valid_commands, f"Invalid command mapping: {ru} -> {en}"


def test_inline_items_titles_start_with_slash():
    for item in INLINE_ITEMS:
        assert item["title"].startswith("/")


def test_match_russian_command():
    from bot.content import match_russian_command
    assert match_russian_command("/мои") == "/my"
    assert match_russian_command("/регистрация") == "/reg"
    assert match_russian_command("/помощь") == "/help"
    assert match_russian_command("/фак") == "/faq"
    assert match_russian_command("/мои_напоминания") == "/my"


def test_match_russian_command_no_match():
    from bot.content import match_russian_command
    assert match_russian_command("/hello") is None
    assert match_russian_command("/my") is None


def test_match_russian_command_latin_command():
    from bot.content import match_russian_command
    assert match_russian_command("/my") is None
    assert match_russian_command("/reg") is None


def test_match_russian_command_partial():
    from bot.content import match_russian_command
    assert match_russian_command("/тихий") == "/quiet"
    assert match_russian_command("/тихий 2ч") == "/quiet"


def test_match_russian_command_with_bot_name():
    from bot.content import match_russian_command
    assert match_russian_command("/мои@my_reminder_bot") == "/my"


def test_match_russian_command_no_slash():
    from bot.content import match_russian_command
    assert match_russian_command("мои") is None


def test_filter_inline_items_empty_query():
    from bot.content import filter_inline_items
    results = filter_inline_items("")
    assert len(results) == len(INLINE_ITEMS)


def test_filter_inline_items_partial_match():
    from bot.content import filter_inline_items
    results = filter_inline_items("re")
    assert len(results) >= 1
    assert any("reg" in r["title"].lower() for r in results)


def test_filter_inline_items_no_match():
    from bot.content import filter_inline_items
    results = filter_inline_items("xyz123")
    assert len(results) == len(INLINE_ITEMS)  # fallback to all items


def test_faq_get_keyboard():
    from bot.content import get_faq_keyboard
    kb = get_faq_keyboard()
    assert kb is not None
    rows = kb.inline_keyboard
    assert len(rows) == len(FAQ)
    for row in rows:
        assert len(row) == 1
        assert row[0].callback_data.startswith("faq:")


def test_inline_items_have_all_commands():
    from bot.content import INLINE_ITEMS
    commands_in_inline = {item["title"].split()[0] for item in INLINE_ITEMS}
    expected_commands = {"/reg", "/my", "/our", "/del", "/tz", "/quiet", "/who", "/stats", "/help", "/faq"}
    assert commands_in_inline == expected_commands
