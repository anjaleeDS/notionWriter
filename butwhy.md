# notion_writer PRD

*Author: Anja*  
*Contributors: Claude (planning & strategy)*

**How can we use AI to help our users?**  
Use AI to act as a unified thinking and execution partner — routing conversations to the right LLM based on intent, and automatically preserving every meaningful exchange in Notion so context is never lost when switching between AI tools.

**Relevant Documents**
- notion_writer GitHub repo
- MVP Checklist (Claude.ai interactive artifact)
- Notion Insights Log database

---

## 1. About

### TLDR

Right now, having conversations with multiple AI assistants (Claude, ChatGPT, Gemini) means context dies at the end of every session. You have to repeat yourself, re-explain your situation, and manually save anything useful. notion_writer solves this by building a single conversational interface on top of Telegram that routes messages intelligently to the right LLM and automatically writes structured summaries of every session into Notion — so your AI tools share a memory layer for the first time.

### Problem Space

The proliferation of capable LLMs has created a fragmentation problem. Different models are better at different things (Claude for reflection and emotional reasoning, ChatGPT for analysis and planning), but there's no easy way to use them together without losing context between sessions. Notion as a knowledge base is powerful but requires manual input — it only becomes useful if you consistently write to it, which most people don't.

---

## 2. Market Insights

### Market Explanation
The personal AI assistant space is growing rapidly, but most tools are single-model, single-interface experiences. There is a clear gap for orchestration tools that treat multiple LLMs as complementary rather than competing, and that connect AI output to personal knowledge management systems.

### Competitor Analysis

| Tool | What it does | Weakness |
|------|-------------|----------|
| ChatGPT Projects | Persistent memory within ChatGPT | Locked to one LLM |
| Claude Projects | Memory within Claude sessions | Locked to one LLM |
| Mem.ai | AI-powered personal memory | No multi-LLM routing |
| Notion AI | AI inside Notion | Reactive, not proactive capture |
| Zapier AI | Workflow automation | Not conversational |

### Customer Segments
- **Solo knowledge workers** who use multiple AI tools and feel the context fragmentation pain daily
- **Builders/makers** who want to wire up their own AI stack without enterprise tooling
- **Reflective practitioners** (coaches, founders, writers) who want to capture thinking, not just tasks

### User Personas

**Anja — The Builder-Thinker**
- Uses Claude for reflection, ChatGPT for planning and execution
- Primary interface is mobile (Telegram feels natural)
- Wants AI to feel like a persistent collaborator, not a disposable chat session
- Technical enough to build this herself but wants strategy support
- Frustrated that every AI conversation starts from zero

---

## 3. The Problem

### Use Cases
1. **Reflective session**: Thinking through a decision, processing an experience, working through an idea — best suited for Claude
2. **Planning session**: Breaking down a project, writing a task list, analysing options — best suited for ChatGPT
3. **Quick capture**: A thought, a URL, a loose idea that needs to be parked for later — no LLM needed, write straight to Notion

### Pain Points
- Every AI conversation starts from scratch — no memory of who you are or what you've been working on
- Switching between Claude and ChatGPT means manually re-establishing context
- Useful AI conversations disappear — they're not saved anywhere structured
- Notion stays empty because writing to it manually is friction-heavy
- No single "home" for AI interactions — it's scattered across browser tabs, apps, and chat histories

### Problem Statement
Anja spends too much time re-establishing context with AI tools and manually saving useful conversations, and never achieves a coherent, accumulated knowledge base that makes each future AI interaction smarter than the last.

### Mission Statement
Build the simplest possible personal AI infrastructure that makes multi-LLM conversations feel like one continuous, memory-enabled relationship.

---

## 4. The Solution

### Ideation

**Core MVP features:**
- Telegram as single entry point for all AI conversations
- One-tap LLM selector at session start (Claude or ChatGPT)
- Full back-and-forth conversation with chosen LLM
- "done" command closes session and triggers Notion write
- LLM generates structured JSON summary of conversation
- JSON written to Notion Insights Log automatically

**Nice-to-have (post-MVP):**
- Auto-classifier that routes based on message intent (no manual tap)
- Gemini as third LLM option
- Quick capture mode (no conversation, direct Notion write)
- Context injection — pull past Notion entries into current LLM session
- Mobile-first UI upgrade (beyond plain Telegram)
- Slack and email as additional routing targets

### Leveraging AI
AI is essential here, not optional, for two reasons:

1. **Routing intelligence**: Determining whether a message is reflective or analytical requires language understanding — rules won't work for the nuance of natural human expression
2. **Structured summarisation**: Converting a free-flowing conversation into a clean, typed Notion entry (with Title, Type, Status, Source Model, Raw Content) requires generative AI — no template or regex approach captures the semantic meaning

Traditional automation tools (Zapier, Make) can wire up APIs but cannot do either of these things. AI is what makes the "capture" step zero-friction.

### Feature Prioritization (RICE)

| Feature | Reach | Impact | Confidence | Effort | Score |
|---------|-------|--------|------------|--------|-------|
| LLM selector + session routing | 1 | 3 | 90% | 0.5 | 5.4 |
| "done" → Notion write | 1 | 3 | 85% | 1 | 2.55 |
| Claude API integration | 1 | 3 | 95% | 0.5 | 5.7 |
| Auto-classifier routing | 1 | 2 | 60% | 2 | 0.6 |
| Context injection from Notion | 1 | 3 | 70% | 2 | 1.05 |

### AI MVP

**How it works:**
- **Input**: Full conversation transcript (user + LLM messages, in order)
- **Prompt**: System prompt instructs the LLM to return a JSON object matching the Notion schema
- **Output**: Structured JSON with fields: `title`, `type`, `status`, `project`, `source_model`, `next_action`, `outcome`, `raw_content`
- **Validation**: `models.py` validates field values against `VALID_TYPES`, `VALID_STATUS`, `VALID_MODELS`
- **Write**: `writer.py` handles Notion API call

**Notion Schema:**
```json
{
  "title": "Short summary of the conversation",
  "type": "Reflection | Execution",
  "status": "Inbox | Active | Done",
  "project": "optional project name",
  "source_model": "Claude | ChatGPT",
  "next_action": "null or text (Execution only)",
  "outcome": "null or text (Execution only)",
  "raw_content": "Full conversation transcript"
}
```

### Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| Phase 1 | Verify notion_writer works locally — test write to Notion | 🔲 In progress |
| Phase 2 | Deploy notion_writer to DigitalOcean droplet | 🔲 Not started |
| Phase 3 | Upgrade Telegram bot — add Claude API, session routing, "done" command | 🔲 Not started |
| Phase 4 | End-to-end test both LLMs → Notion | 🔲 Not started |
| Phase 5 | Intelligence layer — auto-classifier, context injection, Gemini | 🔲 Future |

### Technical Architecture

```
[Telegram] 
    ↓ webhook
[Bot (DigitalOcean droplet)]
    ↓ session routing
[LLM selector] → ChatGPT (OpenAI API) or Claude (Anthropic API)
    ↓ back-and-forth conversation
["done" command]
    ↓ summarisation prompt
[LLM generates JSON]
    ↓
[writer.py] → [Notion API] → [Insights Log database]
```

### Assumptions & Constraints
- Single user (Anja) — no auth, no multi-tenancy needed for MVP
- DigitalOcean droplet stays as hosting for now (Railway as future option)
- Telegram bot token already exists and is functional
- Notion integration already connected; CRUD code already written
- No auto-classifier in MVP — manual one-tap routing only

### Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Notion schema mismatch breaks writes | High | Medium | Test locally before deploying |
| LLM summarisation produces invalid JSON | High | Medium | Add JSON validation + error fallback message to user |
| Droplet goes down, bot stops | Medium | Low | Railway migration in Phase 5 |
| Session state lost between messages | High | Low | Store session in-memory dict keyed to Telegram chat ID |
| OpenAI/Anthropic API rate limits | Low | Low | MVP is single user, well within free tier limits |

---

## 5. Requirements

### User Journey (MVP)

1. Anja opens Telegram and messages the bot
2. Bot replies: "What are we working on? 1️⃣ Reflecting / 2️⃣ Planning"
3. Anja taps 1 or 2
4. Bot opens session with Claude (1) or ChatGPT (2)
5. Anja has a full back-and-forth conversation
6. Anja sends "done"
7. Bot replies: "Got it — saving to Notion..."
8. Bot calls LLM to summarise conversation into JSON
9. Bot calls writer.py with JSON
10. Notion entry created
11. Bot replies: "Saved ✅" with the entry title

### Functional Requirements
- Bot must maintain session state (which LLM, conversation history) per Telegram chat ID
- Session must lock to chosen LLM until "done" or "/start" is received
- "done" must trigger summarisation before Notion write, not raw transcript dump
- Both LLMs must produce identically structured JSON output
- Failed Notion writes must surface a user-facing error in Telegram (not silent failure)

### Non-Functional Requirements
- **Reliability**: Bot must be always-on; PM2 or equivalent process manager required
- **Latency**: Notion write should complete within 10 seconds of "done"
- **Security**: API keys in .env, never hardcoded; .env not committed to GitHub
- **Maintainability**: Bot and writer.py kept as separate concerns; bot calls writer, doesn't reimplement it

### AI & Data Requirements
- **Data source**: Telegram conversation transcript (in-memory per session)
- **Data type**: Unstructured natural language → structured JSON
- **Privacy**: Raw conversation content stored in Notion (user's own account, under their control)
- **Retention**: No conversation data stored on the droplet after Notion write

---

## 6. Challenges

### Data Availability
Not applicable — this product generates its own data (conversations). No training data required; it uses existing LLM APIs.

### Funding
Personal project. Costs are:
- DigitalOcean droplet: ~$6/month
- OpenAI API: pay-per-use, minimal at single-user volume
- Anthropic API: pay-per-use, minimal at single-user volume
- Notion: free tier sufficient for MVP

### Validation
This is a personal tool — validation is self-referential. Success = Anja actually uses it daily and Notion accumulates useful entries over time without manual effort. The proxy metric is: does Notion start filling up automatically?

---

## 7. Positioning

| Use Case | Pain Point | Solution | Impact |
|----------|------------|----------|--------|
| Reflective conversation | Claude context dies at session end | "done" → auto-save to Notion | Every reflection is preserved and searchable |
| Planning conversation | Switching to ChatGPT loses all prior context | Notion entries available to both LLMs | Continuity across models |
| Quick thought capture | Too much friction to open Notion and type | Future: quick capture mode via Telegram | Zero-friction parking of ideas |
| Review past thinking | Conversations scattered across apps | Structured Notion database, typed and searchable | One place for everything |

---

## 8. Measuring Success

### PM Metrics
- **Daily active use**: Is Anja using the bot every day (or close to it)?
- **Notion entry volume**: How many entries created per week?
- **Session completion rate**: What % of sessions end with "done" (vs. abandoned)?
- **Write success rate**: What % of "done" commands result in a successful Notion write?

### AI-Specific Metrics
- **JSON validity rate**: What % of LLM summarisations produce valid, parseable JSON?
- **Schema match rate**: What % of entries have all required fields populated correctly?
- **Latency**: Time from "done" to "Saved ✅" confirmation

### North Star Metric
**Number of Notion entries created automatically per week.**  
If this number grows and stays consistent, the system is working and being used. Everything else is secondary.

---

## 9. Launching

### Stakeholders
Solo project — Anja is PM, engineer, and sole user. No external stakeholders for MVP.

### Roll-out Strategy

| Phase | Criteria to advance |
|-------|-------------------|
| Local verification | writer.py successfully creates a Notion entry from test JSON |
| Droplet deployment | writer.py successfully creates a Notion entry when run on the droplet |
| Bot upgrade | Both LLMs can complete a full session and write to Notion without errors |
| Daily use | Anja uses the bot as primary AI interface for 1 full week |
| Phase 5 planning | >20 Notion entries created; pattern of use is clear |
