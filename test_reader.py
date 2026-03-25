import json
from reader import get_entry_with_body, query_entries

reflection_page_id = "32d8aee5-07cd-81ce-bc02-c30eef73a84a"

print("=== SINGLE ENTRY WITH BODY ===")
print(json.dumps(get_entry_with_body(reflection_page_id), indent=2))

print("\n=== QUERY ENTRIES ===")
print(json.dumps(query_entries(project="System", entry_type="Reflection", limit=3), indent=2))