# session.py
# In-memory conversation state per Telegram chat_id.
# Does not survive server restarts — Notion is the durable store.

sessions: dict = {}


def get_session(chat_id: int) -> dict:
    if chat_id not in sessions:
        sessions[chat_id] = {
            "state": "idle",
            "model": "Claude",
            "messages": [],
        }
    return sessions[chat_id]


def clear_session(chat_id: int) -> None:
    sessions[chat_id] = {
        "state": "idle",
        "model": "Claude",
        "messages": [],
    }
