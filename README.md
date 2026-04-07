# Notion Writer

Small Python utilities to create pages in a Notion database from normalized JSON entries and to read entries back (metadata plus optional body text from paragraph blocks).

## Requirements

- Python 3
- Packages: `requests`, `python-dotenv`

Install:

```bash
pip install requests python-dotenv
```

## Notion setup

1. Create an [internal integration](https://developers.notion.com/docs/create-a-notion-integration) and copy the **integration token**.
2. Create a **database** (or use an existing one) and **share** it with your integration so it can read/write.
3. Copy the database ID from the database URL (the 32-character hex id after the workspace name and slash).

Your database should expose properties that match what the code sends. The writer expects these **property names and types** (names must match exactly):

| Property      | Type    | Notes                                      |
|---------------|---------|--------------------------------------------|
| Title         | Title   | Required on every page                     |
| Type          | Select  | Options should include `Execution`, `Reflection` |
| Status        | Status  | Options should include `Inbox`, `Active`, `Done` |
| Project       | Text    | Rich text in API                           |
| Source Model  | Select  | e.g. `ChatGPT`, `Claude`                   |
| Next Action   | Text    | Optional; used for `Execution`             |
| Outcome       | Text    | Optional; used for `Execution`             |

Long-form text is stored in the **page body** as paragraph blocks (`raw_content`), not as a separate database property.

## Configuration

Create a `.env` file in the project root (do not commit it):

```env
NOTION_TOKEN=secret_...
NOTION_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Entry JSON shape

Fields validated by the writer:

- `title` (string, required)
- `type`: `Execution` or `Reflection`
- `status`: `Inbox`, `Active`, or `Done`
- `project` (optional string)
- `source_model` (optional; defaults to `ChatGPT` in Notion if omitted)
- `raw_content` (optional; becomes the first paragraph block on the page)
- For `Execution` only: `next_action`, `outcome` (optional strings)

Example (`payload.json`):

```json
{
  "title": "Overcomplicating things",
  "type": "Reflection",
  "status": "Inbox",
  "project": "System",
  "source_model": "Claude",
  "raw_content": "I tend to choose complex tools over simple ones."
}
```

## Usage

**Create a page from a JSON file:**

```bash
python3 writer.py payload.json
```

On success, the script prints the new page URL.

**Query and sample read (CLI):**

```bash
python3 reader.py
```

This queries up to one recent entry and prints a single normalized entry **with** `raw_content` loaded from paragraph blocks.

**Router (orchestration helpers):**

Import `route_action` from `router.py` and call it with an action name and payload dict, for example:

- `save_execution` / `save_reflection` — `payload` must include `"entry": { ... }` (same shape as above; type is forced by the action).
- `load_context` — optional keys: `project`, `entry_type`, `status`, `limit` (default `5`).
- `get_entry` — `payload` must include `"page_id"` (Notion page UUID).
- `get_entry_with_body` — same; returns metadata plus `raw_content` from paragraph blocks.

## Tests

Unit tests for the writer payload live in `test_writer.py`:

```bash
python3 -m unittest -v test_writer.py
```

`test_reader.py` is a small **manual** script that calls the live Notion API (requires valid `.env` and network). It is not a unittest module; run it with `python3 test_reader.py` if you use it.

## Troubleshooting

- **`validation_error` / "X is not a property that exists"**: Add the missing property to your Notion database, or rename it to match the table above, or adjust `build_payload` in `writer.py` (and the corresponding reads in `reader.py`) to match your schema.

## But Why


