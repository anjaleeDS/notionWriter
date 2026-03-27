# bot.py
# Handles Telegram updates and manages the conversation state machine.
#
# States per chat_id:
#   idle     → no active conversation
#   chatting → active conversation with Claude
#
# Commands:
#   /start → welcome message
#   /new   → clear session and start fresh
#   /save  → summarise conversation and write to Notion

import os

import httpx

import llm_client
from session import clear_session, get_session
from writer import create_entry

_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
_TELEGRAM_API = f"https://api.telegram.org/bot{_TOKEN}"


async def _send(chat_id: int, text: str) -> None:
    if len(text) > 4096:
        text = text[:4090] + "…"
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{_TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text},
        )


async def handle_update(update: dict) -> None:
    message = update.get("message")
    if not message:
        return

    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    if not text:
        await _send(chat_id, "I can only read text messages for now — please type your message.")
        return

    # ── commands ──────────────────────────────────────────────────────────────

    if text == "/start":
        await _send(
            chat_id,
            (
                "👋 Hello! I'm your thinking partner.\n\n"
                "Send me anything — a thought, a problem, something you're working through. "
                "I'll respond and we'll talk it out. When you're ready, /save writes the "
                "conversation to Notion.\n\n"
                "/save — save conversation to Notion\n"
                "/new  — start a fresh conversation"
            ),
        )
        return

    if text == "/new":
        clear_session(chat_id)
        await _send(chat_id, "✨ Fresh start. What's on your mind?")
        return

    if text == "/save":
        session = get_session(chat_id)
        if not session["messages"]:
            await _send(chat_id, "Nothing to save yet — start a conversation first.")
            return
        await _send(chat_id, "📝 Saving to Notion…")
        try:
            entry = llm_client.generate_entry(
                session["messages"], source_model=session["model"]
            )
            result = create_entry(entry)
            url = result.get("url", "")
            await _send(chat_id, f"✅ Saved!\n{url}")
        except Exception as e:
            await _send(chat_id, f"❌ Save failed: {e}")
        clear_session(chat_id)
        return

    # ── conversation ──────────────────────────────────────────────────────────

    session = get_session(chat_id)
    session["state"] = "chatting"
    session["messages"].append({"role": "user", "content": text})

    try:
        reply = llm_client.send(session["messages"])
    except Exception as e:
        session["messages"].pop()  # remove the failed user message
        await _send(chat_id, f"❌ Error reaching Claude: {e}")
        return

    session["messages"].append({"role": "assistant", "content": reply})
    await _send(chat_id, reply)
