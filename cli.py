# cli.py
#
# Purpose: command-line interface for notion_writer
#
# Commands:
#   reflect   - save a Reflection entry
#   execute   - save an Execution entry
#   save-json - save an entry from a JSON file (formatter output)
#   list      - query recent entries
#   get       - fetch a single entry by page ID

import argparse
import json
import sys

from router import save_reflection, save_execution, load_context, load_entry, load_entry_with_body
from writer import create_entry


# ── helpers ──────────────────────────────────────────────────────────────────

def print_entry(entry, compact=False):
    if compact:
        status = entry.get("status", "")
        type_  = entry.get("type", "")
        title  = entry.get("title", "(no title)")
        pid    = entry.get("page_id", "")
        url    = entry.get("url", "")
        print(f"[{type_:<12}] [{status:<6}]  {title}")
        print(f"  id : {pid}")
        if url:
            print(f"  url: {url}")
    else:
        print(json.dumps(entry, indent=2))


def confirm_or_abort(entry_type, title):
    print(f"\nAbout to save a {entry_type} entry:")
    print(f"  Title: {title}")
    answer = input("Confirm? [y/N] ").strip().lower()
    if answer != "y":
        print("Aborted.")
        sys.exit(0)


# ── subcommand handlers ───────────────────────────────────────────────────────

def cmd_reflect(args):
    entry = {
        "title":        args.title,
        "status":       args.status,
        "project":      args.project or "",
        "outcome":      args.outcome or "",
        "next_action":  "",
        "source_model": args.model,
        "raw_content":  args.content or "",
    }

    if not args.yes:
        confirm_or_abort("Reflection", args.title)

    result = save_reflection(entry)
    print(f"\nSaved: {result.get('url', result.get('id', 'ok'))}")


def cmd_execute(args):
    entry = {
        "title":        args.title,
        "status":       args.status,
        "project":      args.project or "",
        "next_action":  args.next_action or "",
        "outcome":      args.outcome or "",
        "source_model": args.model,
        "raw_content":  args.content or "",
    }

    if not args.yes:
        confirm_or_abort("Execution", args.title)

    result = save_execution(entry)
    print(f"\nSaved: {result.get('url', result.get('id', 'ok'))}")


def cmd_save_json(args):
    try:
        with open(args.file) as f:
            entry = json.load(f)
    except FileNotFoundError:
        print(f"Error: file not found: {args.file}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in {args.file}: {e}", file=sys.stderr)
        sys.exit(1)

    # Show a preview before saving
    if not args.yes:
        print(f"\nAbout to save from {args.file}:")
        print(f"  Title : {entry.get('title', '(missing)')}")
        print(f"  Type  : {entry.get('type', '(missing)')}")
        print(f"  Status: {entry.get('status', '(missing)')}")
        if entry.get('project'):
            print(f"  Project: {entry.get('project')}")
        answer = input("Confirm? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            sys.exit(0)

    result = create_entry(entry)
    print(f"\nSaved: {result.get('url', result.get('id', 'ok'))}")


def cmd_list(args):
    entries = load_context(
        project=args.project,
        entry_type=args.type,
        status=args.status,
        limit=args.limit,
    )

    if not entries:
        print("No entries found.")
        return

    print(f"\n{len(entries)} entr{'y' if len(entries) == 1 else 'ies'} found:\n")
    for entry in entries:
        print_entry(entry, compact=not args.json)
        print()


def cmd_get(args):
    if args.body:
        entry = load_entry_with_body(args.page_id)
    else:
        entry = load_entry(args.page_id)

    print_entry(entry, compact=False)


# ── help ─────────────────────────────────────────────────────────────────────

def cmd_help(_args=None):
    print("""
notion_writer CLI — quick reference
════════════════════════════════════════════════════════════════

COMMANDS
  reflect    Save a Reflection entry (thought-oriented)
  execute    Save an Execution entry (action-oriented)
  save-json  Save an entry from a JSON file (paste formatter output here)
  list       Query recent entries from Notion
  get        Fetch a single entry by page ID
  help       Show this guide

────────────────────────────────────────────────────────────────
reflect — save a reflection
────────────────────────────────────────────────────────────────
  python3 cli.py reflect --title "My thought" [options]

  Required:
    --title TEXT          Entry title

  Optional:
    --project TEXT        Project name
    --status STATUS       Inbox | Active | Done  (default: Inbox)
    --content TEXT        Full reflection text (goes into page body)
    --outcome TEXT        Outcome field
    --model MODEL         Claude | ChatGPT  (default: Claude)
    -y / --yes            Skip the confirmation prompt

  Example:
    python3 cli.py reflect \\
      --title "On surface-level thinking" \\
      --project "Inner Work" \\
      --content "I noticed today that I keep..."  \\
      --status Inbox -y

────────────────────────────────────────────────────────────────
execute — save an execution entry
────────────────────────────────────────────────────────────────
  python3 cli.py execute --title "Task name" [options]

  Required:
    --title TEXT          Entry title

  Optional:
    --project TEXT        Project name
    --status STATUS       Inbox | Active | Done  (default: Inbox)
    --content TEXT        Full entry text (goes into page body)
    --next-action TEXT    Next action field
    --outcome TEXT        Outcome field
    --model MODEL         Claude | ChatGPT  (default: Claude)
    -y / --yes            Skip the confirmation prompt

  Example:
    python3 cli.py execute \\
      --title "Shipped the new endpoint" \\
      --project "API v2" \\
      --next-action "Write tests" \\
      --status Active -y

────────────────────────────────────────────────────────────────
save-json — save from a JSON file (formatter output)
────────────────────────────────────────────────────────────────
  python3 cli.py save-json payload.json

  This is the bridge between the formatter and Notion.
  Workflow:
    1. Ramble to Claude or ChatGPT (with formatter_prompt.md as system prompt)
    2. Copy the JSON output → paste into payload.json
    3. Run: python3 cli.py save-json payload.json
    4. Confirm and it saves to Notion

  Optional:
    -y / --yes    Skip the confirmation prompt

────────────────────────────────────────────────────────────────
list — query recent entries
────────────────────────────────────────────────────────────────
  python3 cli.py list [filters]

  Optional:
    --project TEXT        Filter by project name
    --type TYPE           Reflection | Execution
    --status STATUS       Inbox | Active | Done
    --limit N             Max results (default: 5)
    --json                Output raw JSON instead of summary view

  Examples:
    python3 cli.py list
    python3 cli.py list --type Reflection --status Active
    python3 cli.py list --project "Inner Work" --limit 10
    python3 cli.py list --json

────────────────────────────────────────────────────────────────
get — fetch a single entry by page ID
────────────────────────────────────────────────────────────────
  python3 cli.py get PAGE_ID [--body]

  The page ID is the 32-char hex string at the end of a Notion URL.
  e.g. https://notion.so/My-Page-Title-32d8aee507cd806689c3d7d493faa825
                                        └─────────── this part ──────────┘

  Optional:
    --body    Also fetch the full page body content (raw_content)

  Examples:
    python3 cli.py get 32d8aee507cd806689c3d7d493faa825
    python3 cli.py get 32d8aee507cd806689c3d7d493faa825 --body

────────────────────────────────────────────────────────────────
TIPS
  • Run `python3 cli.py list` first to find page IDs
  • Use --json with list to pipe output elsewhere
  • Use -y to skip confirmation when scripting
  • Valid statuses:  Inbox  |  Active  |  Done
  • Valid types:     Reflection  |  Execution
  • Valid models:    Claude  |  ChatGPT
════════════════════════════════════════════════════════════════
""")


# ── argument parser ───────────────────────────────────────────────────────────

def build_parser():
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="notion_writer — save and retrieve Notion entries from the terminal",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # ── reflect ──────────────────────────────────────────────────────────────
    p_reflect = sub.add_parser("reflect", help="Save a Reflection entry")
    p_reflect.add_argument("--title",   required=True,  help="Entry title")
    p_reflect.add_argument("--project", default="",     help="Project name")
    p_reflect.add_argument("--status",  default="Inbox",
                           choices=["Inbox", "Active", "Done"], help="Status (default: Inbox)")
    p_reflect.add_argument("--content", default="",     help="Full reflection text (page body)")
    p_reflect.add_argument("--outcome", default="",     help="Outcome field")
    p_reflect.add_argument("--model",   default="Claude",
                           choices=["Claude", "ChatGPT"], help="Source model (default: Claude)")
    p_reflect.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt")

    # ── execute ──────────────────────────────────────────────────────────────
    p_execute = sub.add_parser("execute", help="Save an Execution entry")
    p_execute.add_argument("--title",       required=True, help="Entry title")
    p_execute.add_argument("--project",     default="",    help="Project name")
    p_execute.add_argument("--status",      default="Inbox",
                           choices=["Inbox", "Active", "Done"], help="Status (default: Inbox)")
    p_execute.add_argument("--content",     default="",    help="Full entry text (page body)")
    p_execute.add_argument("--next-action", default="",    dest="next_action",
                                                           help="Next action field")
    p_execute.add_argument("--outcome",     default="",    help="Outcome field")
    p_execute.add_argument("--model",       default="Claude",
                           choices=["Claude", "ChatGPT"], help="Source model (default: Claude)")
    p_execute.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt")

    # ── list ─────────────────────────────────────────────────────────────────
    p_list = sub.add_parser("list", help="Query recent entries")
    p_list.add_argument("--project", default=None, help="Filter by project")
    p_list.add_argument("--type",    default=None,
                        choices=["Reflection", "Execution"], help="Filter by type")
    p_list.add_argument("--status",  default=None,
                        choices=["Inbox", "Active", "Done"], help="Filter by status")
    p_list.add_argument("--limit",   default=5, type=int,   help="Max results (default: 5)")
    p_list.add_argument("--json",    action="store_true",   help="Output raw JSON")

    # ── save-json ────────────────────────────────────────────────────────────
    p_savejson = sub.add_parser("save-json", help="Save an entry from a JSON file (formatter output)")
    p_savejson.add_argument("file", help="Path to JSON file (e.g. payload.json)")
    p_savejson.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt")

    # ── get ──────────────────────────────────────────────────────────────────
    p_get = sub.add_parser("get", help="Fetch a single entry by page ID")
    p_get.add_argument("page_id", help="Notion page ID (32-char hex or UUID format)")
    p_get.add_argument("--body", action="store_true", help="Also fetch page body content")

    # ── help ─────────────────────────────────────────────────────────────────
    sub.add_parser("help", help="Show full usage guide")

    return parser


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "reflect":   cmd_reflect,
        "execute":   cmd_execute,
        "save-json": cmd_save_json,
        "list":      cmd_list,
        "get":       cmd_get,
        "help":      cmd_help,
    }

    try:
        dispatch[args.command](args)
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
