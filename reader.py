# reader.py

# Purpose: fetch normalized context from Notion

# It should:
# #search/query by project, type, status, title, recency
# #fetch a single page by ID
# #return clean normalized JSON

# It should NOT:
# #decide what context matters
# #summarize intelligently
# #write anything
import os
import requests
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


def _extract_plain_text(rich_text_list):
    if not rich_text_list:
        return ""
    return "".join(item.get("plain_text", "") for item in rich_text_list)


def _safe_get_name(value):
    if isinstance(value, dict):
        return value.get("name", "")
    return ""


def normalize_notion_page(page):
    props = page.get("properties", {})

    title_items = props.get("Title", {}).get("title", [])
    project_items = props.get("Project", {}).get("rich_text", [])
    next_action_items = props.get("Next Action", {}).get("rich_text", [])
    outcome_items = props.get("Outcome", {}).get("rich_text", [])

    type_value = props.get("Type", {}).get("select")
    status_value = props.get("Status", {}).get("status")
    source_model_value = props.get("Source Model", {}).get("select")

    return {
        "page_id": page.get("id", ""),
        "title": _extract_plain_text(title_items),
        "type": _safe_get_name(type_value),
        "status": _safe_get_name(status_value),
        "project": _extract_plain_text(project_items),
        "next_action": _extract_plain_text(next_action_items),
        "outcome": _extract_plain_text(outcome_items),
        "source_model": _safe_get_name(source_model_value),
        "url": page.get("url", ""),
    }


def query_entries(project=None, entry_type=None, status=None, limit=5):
    filter_conditions = []

    if project:
        filter_conditions.append({
            "property": "Project",
            "rich_text": {"contains": project}
        })

    if entry_type:
        filter_conditions.append({
            "property": "Type",
            "select": {"equals": entry_type}
        })

    if status:
        filter_conditions.append({
            "property": "Status",
            "status": {"equals": status}
        })

    query = {
        "page_size": limit,
        "sorts": [
            {
                "timestamp": "last_edited_time",
                "direction": "descending"
            }
        ]
    }

    if len(filter_conditions) == 1:
        query["filter"] = filter_conditions[0]
    elif len(filter_conditions) > 1:
        query["filter"] = {"and": filter_conditions}

    res = requests.post(
        f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query",
        headers=HEADERS,
        json=query,
        timeout=30,
    )

    if not res.ok:
        raise Exception(f"Notion query failed: {res.status_code} {res.text}")

    data = res.json()
    return [normalize_notion_page(page) for page in data.get("results", [])]


def get_entry(page_id):
    res = requests.get(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=HEADERS,
        timeout=30,
    )

    if not res.ok:
        raise Exception(f"Notion get page failed: {res.status_code} {res.text}")

    return normalize_notion_page(res.json())

def get_page_blocks(page_id):
    res = requests.get(
        f"https://api.notion.com/v1/blocks/{page_id}/children",
        headers=HEADERS,
        timeout=30,
    )

    if not res.ok:
        raise Exception(f"Notion get blocks failed: {res.status_code} {res.text}")

    return res.json().get("results", [])

def extract_paragraph_text(blocks):
    parts = []

    for block in blocks:
        block_type = block.get("type")

        if block_type == "paragraph":
            rich_text = block.get("paragraph", {}).get("rich_text", [])
            parts.append(_extract_plain_text(rich_text))

    return "\n".join(part for part in parts if part)

def get_entry_with_body(page_id):
    entry = get_entry(page_id)
    blocks = get_page_blocks(page_id)
    entry["raw_content"] = extract_paragraph_text(blocks)
    return entry

if __name__ == "__main__":
    import json
    entries = query_entries(limit=1)

    if entries:
        page_id = entries[0]["page_id"]
        print(json.dumps(get_entry_with_body(page_id), indent=2))
    else:
        print("No entries found.")