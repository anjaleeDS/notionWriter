import unittest
import unittest.mock

from writer import build_paragraph_blocks, build_payload, validate_entry, _check_env


# ---------------------------------------------------------------------------
# build_paragraph_blocks
# ---------------------------------------------------------------------------

class BuildParagraphBlocksTests(unittest.TestCase):
    """Tests for the new chunked-body helper (fixes conversation truncation)."""

    def _text_of(self, block):
        """Extract plain text from a paragraph block."""
        rt = block["paragraph"]["rich_text"]
        return rt[0]["text"]["content"] if rt else ""

    def test_empty_string_returns_one_empty_block(self):
        blocks = build_paragraph_blocks("")
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["paragraph"]["rich_text"], [])

    def test_none_returns_one_empty_block(self):
        blocks = build_paragraph_blocks(None)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["paragraph"]["rich_text"], [])

    def test_short_text_returns_single_block(self):
        text = "Hello world"
        blocks = build_paragraph_blocks(text)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(self._text_of(blocks[0]), text)

    def test_exact_chunk_size_is_one_block(self):
        text = "x" * 2000
        blocks = build_paragraph_blocks(text)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(self._text_of(blocks[0]), text)

    def test_long_text_splits_into_multiple_blocks(self):
        # 5001 chars → at least 3 blocks at chunk_size=2000
        text = "a" * 5001
        blocks = build_paragraph_blocks(text)
        self.assertGreaterEqual(len(blocks), 3)

    def test_all_content_is_preserved(self):
        """No characters should be lost or duplicated after splitting."""
        text = "word " * 1000  # 5000 chars
        blocks = build_paragraph_blocks(text)
        rejoined = "".join(self._text_of(b) for b in blocks)
        # Strip both sides: the splitter lstrips newlines between chunks,
        # so we compare trimmed forms to avoid trailing-whitespace noise.
        self.assertEqual(rejoined.strip(), text.strip())

    def test_splits_prefer_newline_over_hard_cut(self):
        """Chunk boundary should fall on a newline when one exists in range."""
        # Build text: 1990 chars + newline + 100 chars  → fits in 2000 with the \n
        line1 = "a" * 1990
        line2 = "b" * 100
        text = line1 + "\n" + line2
        blocks = build_paragraph_blocks(text)
        # First block should be exactly line1 (split at the newline)
        self.assertEqual(self._text_of(blocks[0]), line1)
        self.assertEqual(self._text_of(blocks[1]), line2)

    def test_no_newline_hard_cuts_at_chunk_size(self):
        """When there's no newline in range, fall back to a hard cut."""
        text = "z" * 3000
        blocks = build_paragraph_blocks(text, chunk_size=2000)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(len(self._text_of(blocks[0])), 2000)
        self.assertEqual(len(self._text_of(blocks[1])), 1000)

    def test_blocks_have_correct_notion_structure(self):
        """Each block must have the structure Notion expects."""
        blocks = build_paragraph_blocks("hello")
        block = blocks[0]
        self.assertEqual(block["object"], "block")
        self.assertEqual(block["type"], "paragraph")
        self.assertIn("paragraph", block)
        self.assertIn("rich_text", block["paragraph"])


# ---------------------------------------------------------------------------
# Outcome written for all entry types
# ---------------------------------------------------------------------------

class OutcomeWrittenForAllTypesTests(unittest.TestCase):
    """Outcome should now appear in Notion payload for both Reflection and Execution."""

    def _base_entry(self, entry_type, outcome="The user gained clarity."):
        return {
            "title": "Test",
            "type": entry_type,
            "status": "Inbox",
            "source_model": "Claude",
            "outcome": outcome,
        }

    def test_outcome_written_for_reflection(self):
        entry = self._base_entry("Reflection")
        payload = build_payload(entry)
        self.assertIn("Outcome", payload["properties"])
        text = payload["properties"]["Outcome"]["rich_text"][0]["text"]["content"]
        self.assertEqual(text, entry["outcome"])

    def test_outcome_written_for_execution(self):
        entry = self._base_entry("Execution")
        payload = build_payload(entry)
        self.assertIn("Outcome", payload["properties"])

    def test_outcome_omitted_when_empty_string(self):
        entry = self._base_entry("Reflection", outcome="")
        payload = build_payload(entry)
        self.assertNotIn("Outcome", payload["properties"])

    def test_outcome_omitted_when_missing(self):
        entry = {
            "title": "Test", "type": "Reflection",
            "status": "Inbox", "source_model": "Claude",
        }
        payload = build_payload(entry)
        self.assertNotIn("Outcome", payload["properties"])

    def test_next_action_not_written_for_reflection(self):
        entry = {**self._base_entry("Reflection"), "next_action": "Do something"}
        payload = build_payload(entry)
        self.assertNotIn("Next Action", payload["properties"])

    def test_next_action_written_for_execution(self):
        entry = {**self._base_entry("Execution"), "next_action": "Ship it"}
        payload = build_payload(entry)
        self.assertIn("Next Action", payload["properties"])


# ---------------------------------------------------------------------------
# Date field written to Notion payload
# ---------------------------------------------------------------------------

class DateFieldTests(unittest.TestCase):
    """Date property should be written when present; omitted safely for old fixtures."""

    def _base_entry(self, include_date=True):
        entry = {
            "title": "Test",
            "type": "Reflection",
            "status": "Inbox",
            "source_model": "Claude",
        }
        if include_date:
            entry["date"] = "2026-03-28"
        return entry

    def test_date_written_to_payload(self):
        entry = self._base_entry(include_date=True)
        payload = build_payload(entry)
        self.assertIn("Date", payload["properties"])
        start = payload["properties"]["Date"]["date"]["start"]
        self.assertEqual(start, "2026-03-28")

    def test_date_omitted_when_not_present(self):
        """Old fixtures without a date key should not cause a KeyError."""
        entry = self._base_entry(include_date=False)
        payload = build_payload(entry)
        self.assertNotIn("Date", payload["properties"])

    def test_date_omitted_when_empty_string(self):
        entry = {**self._base_entry(), "date": ""}
        payload = build_payload(entry)
        self.assertNotIn("Date", payload["properties"])


# ---------------------------------------------------------------------------
# Existing tests (unchanged behaviour)
# ---------------------------------------------------------------------------

class BuildPayloadTests(unittest.TestCase):
    def test_reflection_payload_uses_body_for_raw_content(self):
        entry = {
            "title": "Overcomplicating things",
            "type": "Reflection",
            "status": "Inbox",
            "project": "System",
            "source_model": "Claude",
            "raw_content": "I tend to choose complex tools over simple ones.",
        }

        payload = build_payload(entry)

        self.assertNotIn("Raw Content", payload["properties"])
        body_text = payload["children"][0]["paragraph"]["rich_text"][0]["text"]["content"]
        self.assertEqual(body_text, entry["raw_content"])


class EnvVarValidationTests(unittest.TestCase):
    def test_raises_if_notion_token_missing(self):
        with unittest.mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                _check_env()
            self.assertIn("NOTION_TOKEN", str(ctx.exception))

    def test_raises_if_database_id_missing(self):
        with unittest.mock.patch.dict("os.environ", {"NOTION_TOKEN": "tok"}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                _check_env()
            self.assertIn("NOTION_DATABASE_ID", str(ctx.exception))

    def test_passes_when_both_vars_set(self):
        with unittest.mock.patch.dict("os.environ", {"NOTION_TOKEN": "tok", "NOTION_DATABASE_ID": "db"}):
            _check_env()  # should not raise


class ValidateEntryTests(unittest.TestCase):
    def test_missing_type_raises_value_error(self):
        entry = {"status": "Inbox"}
        with self.assertRaises(ValueError) as ctx:
            validate_entry(entry)
        self.assertIn("type", str(ctx.exception).lower())

    def test_missing_status_raises_value_error(self):
        entry = {"type": "Reflection"}
        with self.assertRaises(ValueError) as ctx:
            validate_entry(entry)
        self.assertIn("status", str(ctx.exception).lower())

    def test_invalid_type_raises_value_error(self):
        entry = {"type": "BadType", "status": "Inbox"}
        with self.assertRaises(ValueError):
            validate_entry(entry)

    def test_invalid_status_raises_value_error(self):
        entry = {"type": "Reflection", "status": "BadStatus"}
        with self.assertRaises(ValueError):
            validate_entry(entry)


class BuildPayloadEdgeCaseTests(unittest.TestCase):
    def test_missing_title_raises_value_error(self):
        entry = {"type": "Reflection", "status": "Inbox"}
        with self.assertRaises(ValueError) as ctx:
            build_payload(entry)
        self.assertIn("title", str(ctx.exception).lower())


class CreateEntryTests(unittest.TestCase):
    @unittest.mock.patch("writer.requests.post")
    def test_create_entry_passes_timeout(self, mock_post):
        mock_post.return_value = unittest.mock.Mock(
            ok=True, json=lambda: {"url": "https://notion.so/test"}
        )
        from writer import create_entry
        entry = {
            "title": "Test",
            "type": "Reflection",
            "status": "Inbox",
        }
        create_entry(entry)
        _, kwargs = mock_post.call_args
        self.assertIn("timeout", kwargs)
        self.assertEqual(kwargs["timeout"], 30)


if __name__ == "__main__":
    unittest.main(verbosity=2)
