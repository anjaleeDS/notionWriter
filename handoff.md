What this system is

A Telegram bot (Riri) backed by Python + Notion. You talk to Riri, and when
you're ready, /save writes the conversation to your Notion database as either
a Reflection or Execution entry.

The goal is to let Claude serve as a thinking partner and structured note-taker,
with Notion as the persistent memory store.

⸻

Current status — as of 28 March 2026

Working end-to-end
	•	Telegram bot (Riri) live on Railway
	•	/save, /save reflection, /save execution all work
	•	formatter.py converts conversation → structured JSON via Claude
	•	writer.py writes to Notion (properties + page body)
	•	reader.py queries entries and fetches full page body
	•	All 48 unit tests passing

Just fixed this session (all pushed to main)
	•	Source model was sometimes "ChatGPT" for Claude conversations → fixed: Python now
	  overrides whatever the LLM returns with the session-tracked model value
	•	Outcome was never written for Reflection entries → fixed: outcome now written for all types
	•	Long conversations were truncated at 2000 chars → fixed: body now splits into multiple
	  Notion paragraph blocks (up to ~100 blocks / ~200k chars)
	•	No date was captured → fixed: date is Python-injected (datetime.date.today()) and
	  written to a new "Date" property in Notion (Date type — already added to DB)

Still to do / next priorities
	•	Manual testing of the 4 fixes above via Telegram (see test cases below)
	•	reader.py does not yet read back the Date field — add to normalize_notion_page()
	•	Outcome field is in the Notion DB but reader.py may not normalize it for Reflections
	  — check normalize_notion_page() once manual tests pass
	•	router.py is defined but not central to real usage yet

Intentionally deferred
	•	ChatGPT integration (source_model="ChatGPT" path exists but untested end-to-end)
	•	auto-routing / context-aware saves
	•	embeddings / semantic search
	•	Notion API version migration (currently pinned to 2022-06-28)

⸻

Manual tests to run from home

Run these in Telegram with Riri to verify the 4 fixes:

Test 1 — Source model
  Send a reflective message, a few turns, then /save
  ✅ Notion entry → Source Model = Claude (not ChatGPT)

Test 2 — Outcome for Reflections
  Have a reflective conversation with a clear conclusion, then /save
  ✅ Notion entry → Outcome field is populated

Test 3 — Date field
  Any conversation + /save
  ✅ Notion entry → Date = 2026-03-28 (today)

Test 4 — Long conversation not cut off
  Send several long messages, long replies, then /save
  ✅ Notion page body shows full conversation across multiple paragraph blocks

Test 5 — Execution entry still works
  "I just finished X. Next I need to Y." → /save execution
  ✅ Type = Execution, Next Action populated, Outcome populated, Date set

Test 6 — Regression: Reflection has no Next Action
  Reflective conversation → /save reflection
  ✅ Next Action field is empty/absent

⸻

Source of truth

Notion is the persistent store. One database for both Execution and Reflection.
GitHub: https://github.com/anjaleeDS/notionWriter (main branch)
Bot hosted on: Railway

⸻

Notion schema — current working properties

	•	Title        → title
	•	Type         → select (Reflection | Execution)
	•	Status       → status (Inbox | Active | Done)
	•	Project      → rich_text
	•	Next Action  → rich_text (Execution only)
	•	Outcome      → rich_text (all types — as of this session)
	•	Source Model → select (Claude | ChatGPT)
	•	Date         → date (added this session)
	•	Body         → page body (paragraph blocks, not a property)

Important:
	•	Raw content is NOT stored as a Notion property — it goes in the page body
	•	Status is a Notion "status" type, not a "select" type
	•	Notion-Version is pinned to 2022-06-28 (deliberate — do not upgrade yet)

⸻

Normalized entry schema (internal Python dict)

{
  "title": "string",
  "type": "Execution or Reflection",
  "status": "Inbox, Active, or Done",
  "project": "string",
  "next_action": "string",
  "outcome": "string",
  "source_model": "Claude or ChatGPT",
  "date": "YYYY-MM-DD (Python-injected, not LLM-generated)",
  "raw_content": "string"
}

⸻

File responsibilities

bot.py
  Telegram update handler. Manages session state, dispatches /save, /new, /start.
  On /save: calls format_entry() then create_entry(), clears session after save.

session.py
  In-memory session per chat_id: {state, model, messages}.
  Does not survive server restarts — Notion is the durable store.
  model is hardcoded to "Claude" (ChatGPT path not wired in yet).

formatter.py
  Converts message list → structured entry dict via Claude API.
  Always overrides source_model and date from Python after LLM response.

formatter_prompt.md
  System prompt for the formatter LLM. Defines output JSON schema.
  "date" field is documented as Python-injected — LLM should output "".

writer.py
  Validates and writes an entry dict to Notion.
  build_paragraph_blocks() handles body chunking (≤2000 chars/block).
  outcome is written for all entry types.
  next_action is written for Execution entries only.
  Date property guard is safe for old fixtures without the field.

reader.py
  Queries Notion database, normalizes pages, fetches page body blocks.
  NOTE: does not yet normalize the Date field — add in next session.

router.py
  Conceptual orchestration layer. Defined but not central to usage yet.

⸻

Known history / pitfalls

1. Integration / auth: Notion integration must be in the correct workspace and
   explicitly shared with the database.

2. Status type: Notion's "status" type ≠ "select". writer.py uses {"status": {"name": ...}}.

3. Raw Content property: removed — caused schema mismatch. Page body is used instead.

4. Pasted prose in .py files: caused Unicode/syntax errors in an earlier session.
   Keep code files clean of chat formatting artifacts.

5. Reader null safety: some Notion pages return None for nested properties.
   normalize_notion_page() handles this defensively.

6. Source model confusion: formatter LLM sometimes self-identifies as ChatGPT.
   Fixed by overriding entry["source_model"] = source_model in formatter.py.

⸻

Design constraints (strong preferences)

	•	writer and reader stay "dumb" — no routing or inference inside them
	•	router is the brain
	•	do not make writer schema-autodiscovering
	•	do not introduce automatic tool-routing yet
	•	do not upgrade Notion API version until necessary
	•	boring middleware over fake agent sophistication

⸻

Short version

Telegram bot (Riri) → Claude conversation → /save → formatter.py → writer.py → Notion.
48 tests passing. 4 bugs fixed this session. Manual testing still needed.
Next: run manual tests, then add Date to reader normalization.
