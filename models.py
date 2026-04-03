VALID_TYPES = {"Execution", "Reflection"}
VALID_STATUS = {"Inbox", "Active", "Done"}
VALID_MODELS = {"ChatGPT", "Claude"}

# ── LLM model configuration ─────────────────────────────────────────────────

# Conversational models (used during Telegram chat)
CLAUDE_CHAT_MODEL = "claude-haiku-4-5-20251001"
CHAD_CHAT_MODEL = "gpt-4o-mini"
DEFAULT_CHAT_MODEL = CLAUDE_CHAT_MODEL

# Formatter model (used on /save to structure the entry)
FORMATTER_MODEL = CLAUDE_CHAT_MODEL

# Friendly name → API model ID
MODEL_ALIASES = {
    "claude": CLAUDE_CHAT_MODEL,
    "chad": CHAD_CHAT_MODEL,
}

# API model ID → Notion source_model label
MODEL_TO_SOURCE = {
    CLAUDE_CHAT_MODEL: "Claude",
    CHAD_CHAT_MODEL: "ChatGPT",
}

# Conversation length nudge threshold (number of user messages)
MAX_CONVO_TURNS = 10
CONVO_NUDGE_INTERVAL = 5  # repeat nudge every N turns after threshold

# Per-token pricing in USD (per 1M tokens)
MODEL_PRICING = {
    CLAUDE_CHAT_MODEL: {"input": 0.80, "output": 4.00, "cache_read": 0.08},
    CHAD_CHAT_MODEL: {"input": 0.15, "output": 0.60},
}
