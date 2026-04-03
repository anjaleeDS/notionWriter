# bot.py
# Handles Telegram updates and manages the conversation state machine.
#
# States per chat_id:
#   idle     → no active conversation
#   chatting → active conversation
#
# Commands:
#   /start → welcome message
#   /new [chad|claude] → clear session and start fresh (optionally pick model)
#   /save  → summarise conversation and write to Notion

import os

import httpx

import llm_client
from formatter import format_entry
from models import (
    DEFAULT_CHAT_MODEL,
    MAX_CONVO_TURNS,
    CONVO_NUDGE_INTERVAL,
    MODEL_ALIASES,
    MODEL_TO_SOURCE,
)
from session import clear_session, get_session
from usage_tracker import check_budget_warnings, log_usage, link_session_to_page
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
                "/save             — save to Notion (auto-detect type)\n"
                "/save reflection  — save and force type to Reflection\n"
                "/save execution   — save and force type to Execution\n"
                "/new              — start a fresh conversation (Claude Haiku)\n"
                "/new chad         — start with ChatGPT (GPT-4o-mini)\n"
                "/new claude       — start with Claude (Haiku)"
            ),
        )
        return

    if text == "/new" or text.startswith("/new "):
        parts = text.split(maxsplit=1)
        alias = parts[1].lower() if len(parts) > 1 else None

        if alias and alias not in MODEL_ALIASES:
            await _send(chat_id, f"Unknown model '{alias}'. Try /new chad or /new claude.")
            return

        model = MODEL_ALIASES[alias] if alias else DEFAULT_CHAT_MODEL
        label = MODEL_TO_SOURCE.get(model, model)
        clear_session(chat_id, model=model)
        await _send(chat_id, f"✨ Fresh start with {label}. What's on your mind?")
        return

    if text == "/save" or text.startswith("/save "):
        parts = text.split(maxsplit=1)
        arg = parts[1].lower() if len(parts) > 1 else None

        VALID_OVERRIDES = {"reflection": "Reflection", "execution": "Execution"}
        entry_type = VALID_OVERRIDES.get(arg) if arg else None

        if arg and entry_type is None:
            await _send(chat_id, f"I don't recognise '{arg}'. Did you mean /save reflection or /save execution?")
            return

        session = get_session(chat_id)
        if not session["messages"]:
            await _send(chat_id, "Nothing to save yet — start a conversation first.")
            return

        await _send(chat_id, "📝 Saving to Notion…")
        try:
            source_model = session["source_label"]
            entry = format_entry(
                session["messages"],
                source_model=source_model,
                entry_type=entry_type,
                session_id=session["session_id"],
            )
            result = create_entry(entry)
            page_id = result.get("id", "")
            url = result.get("url", "")
            saved_type = entry["type"]

            # Link all conversation log entries to this Notion page
            if page_id:
                link_session_to_page(session["session_id"], page_id)

            await _send(chat_id, f"✅ Saved as {saved_type}!\n{url}")
        except Exception as e:
            await _send(chat_id, f"❌ Save failed: {e}")
        clear_session(chat_id)
        return

    # ── conversation ──────────────────────────────────────────────────────────

    session = get_session(chat_id)
    session["state"] = "chatting"
    session["messages"].append({"role": "user", "content": text})
    session["user_turns"] += 1

    try:
        reply, usage = llm_client.send(session["messages"], model=session["model"])
    except Exception as e:
        session["messages"].pop()  # remove the failed user message
        session["user_turns"] -= 1
        model_label = session["source_label"]
        await _send(chat_id, f"❌ Error reaching {model_label}: {e}")
        return

    # Log usage for this conversational turn
    log_usage(
        model=session["model"],
        phase="conversation",
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        session_id=session["session_id"],
    )

    session["messages"].append({"role": "assistant", "content": reply})
    await _send(chat_id, reply)

    # Conversation length nudge
    turns = session["user_turns"]
    if turns >= MAX_CONVO_TURNS:
        past_threshold = turns - MAX_CONVO_TURNS
        if past_threshold == 0 or past_threshold % CONVO_NUDGE_INTERVAL == 0:
            await _send(
                chat_id,
                f"💡 We're at {turns} messages — longer conversations cost more tokens. "
                "Want to /save this and start fresh?",
            )

    # Budget warning check
    warning = check_budget_warnings()
    if warning:
        await _send(chat_id, warning)
