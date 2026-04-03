# Cost Reduction & Multi-LLM Support

## Context

We ran out of Claude API credits for the entire month. The main cost driver is the Telegram bot integration — every conversational turn calls Claude Sonnet 4.6, and the formatter replays the full transcript on `/save`. This spec addresses cost through model downgrades, multi-LLM routing, usage tracking, and behavioral nudges.

## Design

### 1. Multi-LLM Support (Claude + OpenAI)

**Models:**
- Claude Haiku 4.5 — new default for conversations and formatting
- GPT-4o-mini ("Chad") — alternative conversational model, user-selectable

**User commands:**
- `/new` — starts conversation with Haiku (default)
- `/new chad` — starts conversation with GPT-4o-mini
- `/new claude` — starts conversation with Haiku (explicit)
- User can switch mid-session if needed

**Session changes:**
- `session["model"]` tracks the active model name (e.g., `"claude-haiku"`, `"gpt-4o-mini"`)
- On `/save`, `source_model` is set to `"Claude"` or `"ChatGPT"` based on actual model used

**Configuration:**
- New env var: `OPENAI_API_KEY`
- Constants in `models.py`: `DEFAULT_MODEL`, `CLAUDE_CHAT_MODEL`, `CHAD_CHAT_MODEL`, `FORMATTER_MODEL`

**Files changed:**
- `models.py` — model constants, mapping from friendly names to API model IDs
- `llm_client.py` — add OpenAI client, `send()` accepts model parameter
- `bot.py` — parse `/new chad|claude`, pass model to `send()`
- `session.py` — store active model in session dict

### 2. Formatter Model Downgrade

**Change:** Formatter switches from Sonnet 4.6 to Haiku 4.5 (or GPT-4o-mini, configurable).

- Same `formatter_prompt.md` system prompt
- Same JSON schema output
- Same Python-level overrides for `source_model`, `date`, `entry_type`
- Configurable via `FORMATTER_MODEL` constant in `models.py`

**Files changed:**
- `formatter.py` — use `FORMATTER_MODEL` instead of hardcoded Sonnet
- `models.py` — add `FORMATTER_MODEL` constant

### 3. Prompt Caching (Anthropic)

**Change:** Add `cache_control` to the formatter system prompt for Anthropic calls.

The formatter system prompt (~900 tokens) is identical on every call. Anthropic's prompt caching gives a 90% discount on cached input tokens after the first call in a session.

**Implementation:** Add `cache_control: {"type": "ephemeral"}` to the system message when calling Claude for formatting.

**Files changed:**
- `formatter.py` — add cache_control to system message for Anthropic calls

### 4. Conversation Length Nudge

**Change:** After N turns (configurable, default 10), bot sends a reminder to save.

Message: "We're at {n} messages — longer conversations cost more tokens. Want to `/save` this and start fresh?"

- Not a hard stop — user can keep going
- Nudge repeats every 5 turns after the threshold
- Configurable via `MAX_CONVO_TURNS` constant

**Files changed:**
- `bot.py` — check turn count before responding, send nudge
- `models.py` — add `MAX_CONVO_TURNS` constant (default: 10)

### 5. Usage Tracking & Budget Warnings

**New file:** `usage_tracker.py`

**Per-call logging to `usage_log.json`:**
```json
{
  "timestamp": "2026-04-02T14:30:00Z",
  "model": "claude-haiku-4-5",
  "phase": "conversation|formatting",
  "input_tokens": 450,
  "output_tokens": 200,
  "estimated_cost_usd": 0.0003,
  "notion_page_id": "abc123..."
}
```

- `notion_page_id` is null for conversational calls, populated after `/save` creates the Notion entry
- After `/save`, the tracker updates all conversation-phase log entries for that session with the resulting `notion_page_id` for traceability

**Monthly budget warnings via Telegram:**
- Configurable budget: `MONTHLY_BUDGET_USD` env var (default: $10)
- Warnings at 50%, 80%, 95% thresholds
- Each threshold fires once per month

**CLI command:** `usage` — shows current month's total spend, breakdown by model, number of entries

**Cost calculation:** Based on published per-token pricing for each model, stored as constants in `usage_tracker.py`.

**Files changed:**
- New: `usage_tracker.py` — logging, budget checking, cost calculation
- `llm_client.py` — call tracker after each API response (both Anthropic and OpenAI return usage metadata)
- `bot.py` — check budget thresholds before responding, send warning if crossed
- `cli.py` — add `usage` subcommand
- `writer.py` — after creating Notion entry, pass page_id back to tracker

## Estimated Cost Impact

| Component | Before (Sonnet 4.6) | After (Haiku 4.5 default) | Savings |
|-----------|---------------------|---------------------------|---------|
| Conversational input | $3/M tokens | $0.80/M tokens | ~73% |
| Conversational output | $15/M tokens | $4/M tokens | ~73% |
| Formatter input | $3/M tokens | $0.80/M tokens | ~73% |
| Formatter output | $15/M tokens | $4/M tokens | ~73% |
| Cached formatter prompt | $3/M tokens | $0.08/M tokens | ~97% |
| Chad (GPT-4o-mini) input | N/A | $0.15/M tokens | — |
| Chad (GPT-4o-mini) output | N/A | $0.60/M tokens | — |

**Overall:** ~70-80% cost reduction from model downgrade alone. Prompt caching and conversation nudges add incremental savings.

## Verification

1. **Multi-LLM:** Start conversations with `/new`, `/new chad`, `/new claude` — verify different models respond and `source_model` is correctly set on saved entries
2. **Formatter:** Save entries and verify JSON quality is acceptable with Haiku
3. **Usage tracking:** Check `usage_log.json` after saving entries — verify token counts and cost estimates are populated
4. **Budget warnings:** Set `MONTHLY_BUDGET_USD=0.01` temporarily, make a few calls, verify Telegram warning messages appear
5. **Conversation nudge:** Have a 10+ turn conversation, verify nudge message appears
6. **Traceability:** Save an entry, find its `notion_page_id` in the usage log, confirm it matches the Notion page
