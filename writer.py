# writer.py

# Purpose: write normalized entries into Notion

# It should:
# #validate required fields
# #map normalized entry JSON → Notion properties/body
# #create new pages
# #optionally update existing pages

# It should NOT:
# #decide whether something deserves saving
# #decide reflection vs execution
# #choose model
# #perform semantic reasoning

import os
import requests
from dotenv import load_dotenv
from models import VALID_TYPES, VALID_STATUS

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")


def _check_env():
    if not os.getenv("NOTION_TOKEN"):
        raise RuntimeError("NOTION_TOKEN is not set. Add it to your .env file.")
    if not os.getenv("NOTION_DATABASE_ID"):
        raise RuntimeError("NOTION_DATABASE_ID is not set. Add it to your .env file.")


if NOTION_TOKEN is None or NOTION_DATABASE_ID is None:
    _check_env()

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


def build_paragraph_blocks(text, chunk_size=2000):
    """Split text into Notion paragraph blocks of at most chunk_size chars.

    Notion's rich_text limit is 2000 chars per text object. Long conversations
    are split on the last newline within each window (falling back to a hard cut)
    so paragraphs stay readable. Returns at least one block (empty if no text).

    Note: Notion allows up to 100 children blocks per API request. At 2000
    chars per block that's ~200,000 chars — enough for any realistic conversation.
    """
    if not text:
        return [{"object": "block", "type": "paragraph",
                 "paragraph": {"rich_text": []}}]
    blocks = []
    while text:
        if len(text) <= chunk_size:
            chunk, text = text, ""
        else:
            split = text.rfind("\n", 0, chunk_size)
            split = split if split > 0 else chunk_size
            chunk, text = text[:split], text[split:].lstrip("\n")
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]}
        })
    return blocks


def build_rich_text(value):
    if not value:
        return []
    return [{"type": "text", "text": {"content": value[:2000]}}]


def validate_entry(entry):
    entry_type = entry.get("type")
    entry_status = entry.get("status")
    if entry_type not in VALID_TYPES:
        raise ValueError(f"Invalid or missing type: {entry_type!r}. Must be one of: {VALID_TYPES}")
    if entry_status not in VALID_STATUS:
        raise ValueError(f"Invalid or missing status: {entry_status!r}. Must be one of: {VALID_STATUS}")


def build_payload(entry):
    title = entry.get("title")
    if not title:
        raise ValueError("Entry must have a non-empty 'title' field.")

    properties = {
        "Title": {
            "title": [{"text": {"content": title}}]
        },
        "Type": {
            "select": {"name": entry["type"]}
        },
        "Status": {
            "status": {"name": entry["status"]}
        },
        "Project": {
            "rich_text": build_rich_text(entry.get("project"))
        },
        "Source Model": {
            "select": {"name": entry.get("source_model", "Claude")}
        }
    }

    # next_action is Execution-only
    if entry["type"] == "Execution":
        if entry.get("next_action"):
            properties["Next Action"] = {
                "rich_text": build_rich_text(entry["next_action"])
            }

    # outcome is written for all entry types (Reflection and Execution)
    if entry.get("outcome"):
        properties["Outcome"] = {
            "rich_text": build_rich_text(entry["outcome"])
        }

    # date is Python-injected; guard makes this safe for old fixtures without the field
    if entry.get("date"):
        properties["Date"] = {
            "date": {"start": entry["date"]}
        }

    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": properties,
        "children": build_paragraph_blocks(entry.get("raw_content", ""))
    }

    return payload


def create_entry(entry):
    validate_entry(entry)
    payload = build_payload(entry)

    response = requests.post(
        "https://api.notion.com/v1/pages",
        headers=HEADERS,
        json=payload,
        timeout=30,
    )

    if not response.ok:
        raise Exception(response.text)

    return response.json()


if __name__ == "__main__":
    import json
    import sys

    with open(sys.argv[1]) as f:
        entry = json.load(f)

    result = create_entry(entry)
    print("Created:", result["url"])