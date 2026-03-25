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

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


def build_rich_text(value):
    if not value:
        return []
    return [{"type": "text", "text": {"content": value[:2000]}}]


def validate_entry(entry):
    if entry["type"] not in VALID_TYPES:
        raise ValueError("Invalid type")
    if entry["status"] not in VALID_STATUS:
        raise ValueError("Invalid status")


def build_payload(entry):
    properties = {
        "Title": {
            "title": [{"text": {"content": entry["title"]}}]
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
            "select": {"name": entry.get("source_model", "ChatGPT")}
        }
    }

    if entry["type"] == "Execution":
        if entry.get("next_action"):
            properties["Next Action"] = {
                "rich_text": build_rich_text(entry["next_action"])
            }
        if entry.get("outcome"):
            properties["Outcome"] = {
                "rich_text": build_rich_text(entry["outcome"])
            }

    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": properties,
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": build_rich_text(entry.get("raw_content"))
                }
            }
        ]
    }

    return payload


def create_entry(entry):
    validate_entry(entry)
    payload = build_payload(entry)

    response = requests.post(
        "https://api.notion.com/v1/pages",
        headers=HEADERS,
        json=payload
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