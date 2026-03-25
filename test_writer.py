import unittest

from writer import build_payload


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


if __name__ == "__main__":
    unittest.main()
