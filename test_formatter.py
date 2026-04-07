import datetime
import json
import unittest
import unittest.mock

# Patch the Anthropic client before importing formatter so the SDK
# never tries to initialise (avoids needing a real API key in CI).
with unittest.mock.patch("anthropic.Anthropic"):
    import formatter


def _make_usage():
    """Build a fake Anthropic usage object."""
    usage = unittest.mock.Mock()
    usage.input_tokens = 100
    usage.output_tokens = 50
    usage.cache_read_input_tokens = 0
    return usage


def _make_response(entry: dict) -> unittest.mock.Mock:
    """Build a fake Anthropic response containing a JSON entry."""
    msg = unittest.mock.Mock()
    msg.content = [unittest.mock.Mock(text=json.dumps(entry))]
    msg.usage = _make_usage()
    return msg


def _make_fenced_response(entry: dict) -> unittest.mock.Mock:
    """Build a fake response where the JSON is wrapped in markdown fences."""
    msg = unittest.mock.Mock()
    msg.content = [unittest.mock.Mock(text=f"```json\n{json.dumps(entry)}\n```")]
    msg.usage = _make_usage()
    return msg


def _make_preamble_response(entry: dict) -> unittest.mock.Mock:
    """Build a fake response where Claude adds prose before the JSON object."""
    msg = unittest.mock.Mock()
    msg.content = [unittest.mock.Mock(
        text=f"I'll format this from the conversation available.\n\n{json.dumps(entry)}"
    )]
    msg.usage = _make_usage()
    return msg


def _mock_anthropic_formatter(response):
    """Return a context manager that mocks the formatter to use a fake Anthropic client.

    This patches both _is_anthropic_model (to force the Anthropic branch)
    and _get_anthropic_client (to return a fake client with the given response).
    """
    mock_client = unittest.mock.Mock()
    mock_client.messages.create.return_value = response
    return unittest.mock.patch.multiple(
        "formatter",
        _is_anthropic_model=unittest.mock.Mock(return_value=True),
        _get_anthropic_client=unittest.mock.Mock(return_value=mock_client),
    )


# ---------------------------------------------------------------------------
# Source model override
# ---------------------------------------------------------------------------

class SourceModelOverrideTests(unittest.TestCase):
    """Python-passed source_model must always win over whatever the LLM returns."""

    base_entry = {
        "title": "Test",
        "type": "Reflection",
        "status": "Inbox",
        "project": "",
        "next_action": "",
        "outcome": "",
        "source_model": "ChatGPT",   # LLM wrongly says ChatGPT
        "raw_content": "User: hi. Assistant: hello.",
    }

    def test_claude_default_overrides_llm_chatgpt(self):
        """Default source_model='Claude' should overwrite LLM's 'ChatGPT'."""
        with _mock_anthropic_formatter(_make_response(self.base_entry)):
            result = formatter.format_entry([{"role": "user", "content": "hi"}])
        self.assertEqual(result["source_model"], "Claude")

    def test_explicit_claude_param_overrides_llm_chatgpt(self):
        """Explicit source_model='Claude' should overwrite LLM's 'ChatGPT'."""
        with _mock_anthropic_formatter(_make_response(self.base_entry)):
            result = formatter.format_entry(
                [{"role": "user", "content": "hi"}],
                source_model="Claude",
            )
        self.assertEqual(result["source_model"], "Claude")

    def test_chatgpt_param_is_respected(self):
        """If Python explicitly passes 'ChatGPT', that should be the result."""
        entry = {**self.base_entry, "source_model": "Claude"}  # LLM says Claude
        with _mock_anthropic_formatter(_make_response(entry)):
            result = formatter.format_entry(
                [{"role": "user", "content": "hi"}],
                source_model="ChatGPT",
            )
        self.assertEqual(result["source_model"], "ChatGPT")


# ---------------------------------------------------------------------------
# Date injection
# ---------------------------------------------------------------------------

class DateInjectionTests(unittest.TestCase):
    """Today's date must always be injected by Python, never from the LLM."""

    base_entry = {
        "title": "Test",
        "type": "Reflection",
        "status": "Inbox",
        "project": "",
        "next_action": "",
        "outcome": "",
        "source_model": "Claude",
        "raw_content": "User: hi. Assistant: hello.",
    }

    def test_date_is_injected_as_today(self):
        with _mock_anthropic_formatter(_make_response(self.base_entry)):
            result = formatter.format_entry([{"role": "user", "content": "hi"}])
        self.assertEqual(result["date"], datetime.date.today().isoformat())

    def test_date_overrides_any_llm_value(self):
        """Even if LLM returns a date, Python's value wins."""
        entry = {**self.base_entry, "date": "1999-01-01"}
        with _mock_anthropic_formatter(_make_response(entry)):
            result = formatter.format_entry([{"role": "user", "content": "hi"}])
        self.assertEqual(result["date"], datetime.date.today().isoformat())

    def test_date_format_is_iso(self):
        """Date must be in YYYY-MM-DD format."""
        with _mock_anthropic_formatter(_make_response(self.base_entry)):
            result = formatter.format_entry([{"role": "user", "content": "hi"}])
        # Validate it parses back cleanly as an ISO date
        parsed = datetime.date.fromisoformat(result["date"])
        self.assertEqual(parsed, datetime.date.today())


# ---------------------------------------------------------------------------
# Entry type override (existing tests, updated for new fields)
# ---------------------------------------------------------------------------

class FormatEntryTypeOverrideTests(unittest.TestCase):
    """Core new behaviour: entry_type stomps the formatter's own type field."""

    def setUp(self):
        self.base_entry = {
            "title": "Test entry",
            "type": "Execution",   # formatter thinks it's Execution
            "status": "Inbox",
            "project": "",
            "next_action": "ship it",
            "outcome": "",
            "source_model": "Claude",
            "raw_content": "User: I finished the feature. Assistant: Great work.",
        }

    def test_no_override_returns_formatter_type(self):
        """With no entry_type arg, the formatter's own type is kept."""
        with _mock_anthropic_formatter(_make_response(self.base_entry)):
            result = formatter.format_entry([{"role": "user", "content": "test"}])
        self.assertEqual(result["type"], "Execution")

    def test_reflection_override_stomps_execution(self):
        """entry_type='Reflection' overrides even when formatter says Execution."""
        with _mock_anthropic_formatter(_make_response(self.base_entry)):
            result = formatter.format_entry(
                [{"role": "user", "content": "test"}],
                entry_type="Reflection",
            )
        self.assertEqual(result["type"], "Reflection")

    def test_execution_override_stomps_reflection(self):
        """entry_type='Execution' overrides even when formatter says Reflection."""
        entry = {**self.base_entry, "type": "Reflection"}
        with _mock_anthropic_formatter(_make_response(entry)):
            result = formatter.format_entry(
                [{"role": "user", "content": "test"}],
                entry_type="Execution",
            )
        self.assertEqual(result["type"], "Execution")

    def test_none_override_does_not_change_type(self):
        """Explicitly passing entry_type=None leaves the formatter's type intact."""
        with _mock_anthropic_formatter(_make_response(self.base_entry)):
            result = formatter.format_entry(
                [{"role": "user", "content": "test"}],
                entry_type=None,
            )
        self.assertEqual(result["type"], "Execution")

    def test_other_fields_are_preserved_after_override(self):
        """Type override should not affect title, status, or raw_content."""
        with _mock_anthropic_formatter(_make_response(self.base_entry)):
            result = formatter.format_entry(
                [{"role": "user", "content": "test"}],
                entry_type="Reflection",
            )
        self.assertEqual(result["title"], self.base_entry["title"])
        self.assertEqual(result["status"], self.base_entry["status"])
        self.assertEqual(result["raw_content"], self.base_entry["raw_content"])
        # source_model is always overridden by Python — default is "Claude"
        self.assertEqual(result["source_model"], "Claude")


# ---------------------------------------------------------------------------
# JSON parsing (existing tests, unchanged)
# ---------------------------------------------------------------------------

class FormatEntryJsonParsingTests(unittest.TestCase):
    """Formatter correctly handles raw JSON and fenced JSON responses."""

    base_entry = {
        "title": "Fenced test",
        "type": "Reflection",
        "status": "Inbox",
        "project": "",
        "next_action": "",
        "outcome": "",
        "source_model": "Claude",
        "raw_content": "some text",
    }

    def test_plain_json_is_parsed(self):
        with _mock_anthropic_formatter(_make_response(self.base_entry)):
            result = formatter.format_entry([{"role": "user", "content": "hi"}])
        self.assertEqual(result["title"], "Fenced test")

    def test_fenced_json_is_stripped_and_parsed(self):
        with _mock_anthropic_formatter(_make_fenced_response(self.base_entry)):
            result = formatter.format_entry([{"role": "user", "content": "hi"}])
        self.assertEqual(result["title"], "Fenced test")

    def test_prose_preamble_is_stripped_and_parsed(self):
        """Regression: Claude prefixes JSON with prose — should still parse correctly."""
        with _mock_anthropic_formatter(_make_preamble_response(self.base_entry)):
            result = formatter.format_entry([{"role": "user", "content": "hi"}])
        self.assertEqual(result["title"], "Fenced test")


# ---------------------------------------------------------------------------
# /save command parsing (existing tests, unchanged)
# ---------------------------------------------------------------------------

class SaveCommandParsingTests(unittest.TestCase):
    """/save command parsing logic — tests the VALID_OVERRIDES lookup directly."""

    VALID_OVERRIDES = {"reflection": "Reflection", "execution": "Execution"}

    def _parse(self, text):
        """Mirror the parsing logic in bot.py handle_update()."""
        parts = text.split(maxsplit=1)
        arg = parts[1].lower() if len(parts) > 1 else None
        entry_type = self.VALID_OVERRIDES.get(arg) if arg else None
        unknown = arg is not None and entry_type is None
        return arg, entry_type, unknown

    def test_bare_save_has_no_arg(self):
        arg, entry_type, unknown = self._parse("/save")
        self.assertIsNone(arg)
        self.assertIsNone(entry_type)
        self.assertFalse(unknown)

    def test_save_reflection_lowercases_correctly(self):
        _, entry_type, unknown = self._parse("/save reflection")
        self.assertEqual(entry_type, "Reflection")
        self.assertFalse(unknown)

    def test_save_execution_lowercases_correctly(self):
        _, entry_type, unknown = self._parse("/save execution")
        self.assertEqual(entry_type, "Execution")
        self.assertFalse(unknown)

    def test_save_reflection_mixed_case(self):
        _, entry_type, unknown = self._parse("/save Reflection")
        self.assertEqual(entry_type, "Reflection")
        self.assertFalse(unknown)

    def test_unknown_type_flagged(self):
        """Unknown arg is flagged so bot can reply with a clarifying prompt."""
        _, entry_type, unknown = self._parse("/save braindump")
        self.assertIsNone(entry_type)
        self.assertTrue(unknown)

    def test_unknown_type_does_not_match_partial(self):
        """Partial match like 'reflect' is still treated as unknown."""
        _, entry_type, unknown = self._parse("/save reflect")
        self.assertIsNone(entry_type)
        self.assertTrue(unknown)


if __name__ == "__main__":
    unittest.main(verbosity=2)
