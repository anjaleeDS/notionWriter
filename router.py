# router.py

# Purpose: orchestrate behavior

# It should:
# #decide whether to read first
# #decide whether to write
# #decide whether to create or update
# #decide what payload to send to writer/reader
# #optionally decide which model handles the thinking

# It should NOT:
# #directly know Notion field mapping details
# #embed database-specific quirks
from writer import create_entry
from reader import query_entries, get_entry, get_entry_with_body

def save_execution(entry):
    entry["type"] = "Execution"
    return create_entry(entry)

def load_entry_with_body(page_id):
    return get_entry_with_body(page_id)

def save_reflection(entry):
    entry["type"] = "Reflection"
    return create_entry(entry)


def load_context(project=None, entry_type=None, status=None, limit=5):
    return query_entries(
        project=project,
        entry_type=entry_type,
        status=status,
        limit=limit,
    )


def load_entry(page_id):
    return get_entry(page_id)


def route_action(action, payload):
    if action == "save_execution":
        return save_execution(payload["entry"])
        
    if action == "get_entry_with_body":
        return load_entry_with_body(payload["page_id"])

    if action == "save_reflection":
        return save_reflection(payload["entry"])

    if action == "load_context":
        return load_context(
            project=payload.get("project"),
            entry_type=payload.get("entry_type"),
            status=payload.get("status"),
            limit=payload.get("limit", 5),
        )

    if action == "get_entry":
        return load_entry(payload["page_id"])

    raise ValueError(f"Unknown action: {action}")


if __name__ == "__main__":
    print(load_context(limit=5))