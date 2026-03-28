import json
import unittest
import unittest.mock

# Patch the Anthropic client before importing formatter so the SDK
# never tries to initialise (avoids needing a real API key in CI).
with unittest.mock.patch("anthropic.Anthropic"):
    import formatter


def _make_response(entry: dict) -> unittest.mock.Mock:
    """Build a fake Anthropic response containing a JSON entry."""
    msg = unittest.mock.Mock()
    msg.content = [unittest.mock.Mock(text=json.dumps(entry))]
    return msg


def _make_fenced_response(entry: dict) -> unittest.mock.Mock:
    """Build a fake response where the JSON is wrapped in markdown fences."""
    msg = unittest.mock.Mock()
    msg.content = [unittest.mock.Mock(text=f"```json\n{json.dumps(entry)}\n```")]
    return msg


def _make_preamble_response(entry: dict) -> unittest.mock.Mock:
    """Build a fake response where Claude adds prose before the JSON object."""
    msg = unittest.mock.Mock()
    msg.content = [unittest.mock.Mock(
        text=f"I'll format this from the conversation available.\n\n{json.dumps(entry)}"
    )]
    return msg


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
        with unittest.mock.patch.object(
            formatter._client.messages, "create",
            return_value=_make_response(self.base_entry),
        ):
            result = formatter.format_entry([{"role": "user", "content": "test"}])
        self.assertEqual(result["type"], "Execution")

    def test_reflection_override_stomps_execution(self):
        """entry_type='Reflection' overrides even when formatter says Execution."""
        with unittest.mock.patch.object(
            formatter._client.messages, "create",
            return_value=_make_response(self.base_entry),
        ):
            result = formatter.format_entry(
                [{"role": "user", "content": "test"}],
                entry_type="Reflection",
            )
        self.assertEqual(result["type"], "Reflection")

    def test_execution_override_stomps_reflection(self):
        """entry_type='Execution' overrides even when formatter says Reflection."""
        entry = {**self.base_entry, "type": "Reflection"}
        with unittest.mock.patch.object(
            formatter._client.messages, "create",
            return_value=_make_response(entry),
        ):
            result = formatter.format_entry(
                [{"role": "user", "content": "test"}],
                entry_type="Execution",
            )
        self.assertEqual(result["type"], "Execution")

    def test_none_override_does_not_change_type(self):
        """Explicitly passing entry_type=None leaves the formatter's type intact."""
        with unittest.mock.patch.object(
            formatter._client.messages, "create",
            return_value=_make_response(self.base_entry),
        ):
            result = formatter.format_entry(
                [{"role": "user", "content": "test"}],
                entry_type=None,
            )
        self.assertEqual(result["type"], "Execution")

    def test_other_fields_are_preserved_after_override(self):
        """Type override should not affect any other field."""
        with unittest.mock.patch.object(
            formatter._client.messages, "create",
            return_value=_make_response(self.base_entry),
        ):
            result = formatter.format_entry(
                [{"role": "user", "content": "test"}],
                entry_type="Reflection",
            )
        self.assertEqual(result["title"], self.base_entry["title"])
        self.assertEqual(result["status"], self.base_entry["status"])
        self.assertEqual(result["source_model"], self.base_entry["source_model"])
        self.assertEqual(result["raw_content"], self.base_entry["raw_content"])


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
        with unittest.mock.patch.object(
            formatter._client.messages, "create",
            return_value=_make_response(self.base_entry),
        ):
            result = formatter.format_entry([{"role": "user", "content": "hi"}])
        self.assertEqual(result["title"], "Fenced test")

    def test_fenced_json_is_stripped_and_parsed(self):
        with unittest.mock.patch.object(
            formatter._client.messages, "create",
            return_value=_make_fenced_response(self.base_entry),
        ):
            result = formatter.format_entry([{"role": "user", "content": "hi"}])
        self.assertEqual(result["title"], "Fenced test")

    def test_prose_preamble_is_stripped_and_parsed(self):
        """Regression: Claude prefixes JSON with prose — should still parse correctly."""
        with unittest.mock.patch.object(
            formatter._client.messages, "create",
            return_value=_make_preamble_response(self.base_entry),
        ):
            result = formatter.format_entry([{"role": "user", "content": "hi"}])
        self.assertEqual(result["title"], "Fenced test")


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
