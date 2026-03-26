What this system is

A local Python-based Notion-backed note system for two note types:
	•	Execution: action-oriented entries
	•	Reflection: thought-oriented entries

The goal is to let different LLMs (currently ChatGPT and Claude) produce structured entries that can be:
	•	written into Notion
	•	queried back from Notion
	•	retrieved with full page-body content when needed

Current status

Working
	•	Local Notion API auth works
	•	writer.py successfully creates Notion pages
	•	reader.py successfully queries entries from Notion
	•	reader.py can also fetch page-body content via block children
	•	Reflection entries are retrievable with raw_content
	•	Schema and Notion property mapping are mostly stable

Intentionally deferred
	•	OpenClaw integration
	•	Telegram interface
	•	auto-routing
	•	direct LLM-to-Notion writes
	•	schema autodiscovery
	•	embeddings/search
	•	hosted API endpoint

⸻

Source of truth

Notion is the persistent store.

One database is being used for both execution and reflection entries.

⸻

Notion schema assumptions

Current working property assumptions:
	•	Title → title
	•	Type → select
	•	Status → status
	•	Project → rich_text
	•	Next Action → rich_text
	•	Outcome → rich_text
	•	Source Model → select

Important:
	•	Reflection raw_content is not stored as a Raw Content property anymore
	•	Reflection and execution body text are stored in the page body
	•	This was changed because Raw Content property caused schema mismatch and duplication
Environment
Important implementation detail:
	•	Notion-Version is currently pinned to 2022-06-28
	•	This is deliberate because the newer Notion API versions introduce database/data-source changes that were not migrated yet

⸻

File responsibilities

writer.py

Purpose:
	•	validate normalized entry payload
	•	map payload to Notion page properties + body
	•	create a page in the configured database

Current behavior:
	•	Execution:
	•	writes properties like Next Action, Outcome
	•	Reflection:
	•	does not write a Raw Content property
	•	stores full reflection text only in page body
	•	Full raw_content goes into page body for both types

Known design decision:
	•	writer should remain “dumb”
	•	no routing or inference inside writer

⸻

reader.py

Purpose:
	•	query Notion database
	•	normalize returned page metadata
	•	fetch full page body when needed

Current working functions:
	•	query_entries(project=None, entry_type=None, status=None, limit=5)
	•	get_entry(page_id)
	•	get_page_blocks(page_id)
	•	extract_paragraph_text(blocks)
	•	get_entry_with_body(page_id)
	•	normalize_notion_page(page)

Current normalization returns fields like:
	•	page_id
	•	title
	•	type
	•	status
	•	project
	•	next_action
	•	outcome
	•	source_model
	•	url

And get_entry_with_body(page_id) adds:
	•	raw_content

Important bug already fixed:
	•	Notion sometimes returns None for property internals
	•	normalization now defensively handles None rather than assuming nested dicts always exist
router.py

Current state:
	•	conceptually defined
	•	not yet the center of real usage
	•	intended to be the orchestration layer between models and I/O

Planned responsibilities:
	•	explicit actions first:
	•	save_execution
	•	save_reflection
	•	load_context
	•	get_entry
	•	get_entry_with_body
	•	maybe later:
	•	auto-route read/write
	•	context-aware save behavior
	•	model selection

Strong design preference:
	•	keep router as brain
	•	keep writer/reader dumb

⸻

Normalized entry schema

Current internal schema expectation:
{
  "title": "string",
  "type": "Execution or Reflection",
  "status": "Inbox, Active, or Done",
  "project": "string",
  "next_action": "string",
  "outcome": "string",
  "source_model": "ChatGPT or Claude",
  "raw_content": "string"
}
Notes:
	•	next_action is often empty for Reflection
	•	outcome is optional / often empty
	•	raw_content is used as the page body content
Important implementation history / pitfalls

1. Notion access issues

Encountered and resolved:
	•	wrong workspace integration
	•	integration not shared with database
	•	wrong database ID

Lesson:
	•	integration must be created in the correct workspace
	•	database must be explicitly shared with the integration

2. Notion Status type mismatch

Problem:
	•	code treated Status as select
	•	actual Notion property type is status

Fix:
	•	writer uses:
    "Status": {
    "status": {"name": status}
}

3. Raw Content property mismatch

Problem:
	•	code tried to write a Notion property called Raw Content
	•	database did not have that property
	•	caused validation errors

Resolution:
	•	removed Raw Content property write
	•	kept body content only

4. Syntax issues from pasted prose

At one point explanatory bullet text got pasted into .py files and caused:
	•	invalid Unicode character errors
	•	invalid syntax from markdown/backticks

Lesson:
	•	code files should contain only code/comments, not chat formatting artifacts

5. Reader null safety

Problem:
	•	some pages returned None for nested property values
	•	normalization failed on chained .get(...)

Fix:
	•	added defensive helper logic for safe extraction

⸻

Developer guidance / design constraints

Preferred principles
	•	one stable schema
	•	explicit contracts over magic
	•	boring middleware over fake agent sophistication
	•	use behavior first, automation second

Strong preferences
	•	do not make writer schema-autodiscovering yet
	•	do not introduce automatic tool-routing yet
	•	do not migrate to newer Notion API version until necessary
	•	do not overbuild around OpenClaw before the core loop is used more

⸻

Suggested next priorities for another developer

High priority
	1.	Clean and harden router.py
	2.	Add basic tests for writer and reader
	3.	Add a simple CLI interface for:
	•	save execution
	•	save reflection
	•	load context
	•	get entry with body
	4.	Standardize JSON formatter prompts for Claude and ChatGPT

Medium priority
	5.	Turn writer into a tiny local API endpoint
	6.	Let Claude skill call formatter only
	7.	Route formatted JSON into writer endpoint

Later
	8.	OpenClaw integration
	9.	Telegram interface
	10.	auto-routing logic
	11.	Notion API version migration

⸻

Suggested immediate deliverables for the next developer

Ask them to produce:
	1.	router.py with explicit action dispatch
	2.	test_writer.py
	3.	test_reader.py
	4.	cli.py or equivalent command wrapper
	5.	optional local Flask/FastAPI endpoint for writer only

⸻

What the user actually wants from the system

Not just note storage.

They want a system where:
	•	ChatGPT helps with execution thinking
	•	Claude helps with reflection thinking
	•	both can format entries into a shared schema
	•	Notion stores and returns those entries as persistent memory
	•	later, a router coordinates read/write behavior

So the product intent is:
structured human-LLM thought management with persistent memory

⸻

Short version for a developer

If you want the compressed handoff:
	•	Local Python + Notion API system
	•	writer.py works
	•	reader.py works, including full body retrieval
	•	Notion version pinned to 2022-06-28
	•	Status is a real Notion status field
	•	Project is rich_text
	•	Raw Content property was removed; page body is used instead
	•	router is next
	•	no auto-routing, OpenClaw, or Telegram yet
	•	keep architecture simple and explicit
