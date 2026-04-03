# session.py
# In-memory conversation state per Telegram chat_id.
# Does not survive server restarts — Notion is the durable store.

import uuid

from models import DEFAULT_CHAT_MODEL, MODEL_TO_SOURCE

sessions: dict = {}


def _new_session(model: str = DEFAULT_CHAT_MODEL) -> dict:
    return {
        "state": "idle",
        "model": model,
        "source_label": MODEL_TO_SOURCE.get(model, "Claude"),
        "messages": [],
        "session_id": str(uuid.uuid4()),
        "user_turns": 0,
    }


def get_session(chat_id: int) -> dict:
    if chat_id not in sessions:
        sessions[chat_id] = _new_session()
    return sessions[chat_id]


def clear_session(chat_id: int, model: str = DEFAULT_CHAT_MODEL) -> None:
    sessions[chat_id] = _new_session(model)
