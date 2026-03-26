import unittest
import unittest.mock

from writer import build_payload, validate_entry, _check_env


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
        self.assertEqual(body_text, entry["raw_content"][:2000])


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
    unittest.main()
