# llm_client.py
# Thin wrapper over the Anthropic SDK (Phase 1: Claude only).
#
# send()           → returns a reply string for an ongoing conversation
# generate_entry() → returns a structured dict ready for writer.create_entry()

import json
import os
from pathlib import Path

import anthropic

_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

_FORMATTER_PROMPT = (Path(__file__).parent / "formatter_prompt.md").read_text()

_CHAT_SYSTEM = (
    "You are a thoughtful conversational assistant. "
    "Engage naturally with the user — be warm, curious, and insightful. "
    "Help them think through whatever is on their mind."
)

CLAUDE_MODEL = "claude-sonnet-4-6"


def send(messages: list[dict]) -> str:
    response = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=_CHAT_SYSTEM,
        messages=messages,
    )
    return response.content[0].text


def generate_entry(messages: list[dict], source_model: str = "Claude") -> dict:
    transcript = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
        for m in messages
    )
    prompt = (
        "The following is a full conversation between a user and an AI assistant. "
        "Generate a Notion entry based on this conversation:\n\n"
        f"{transcript}"
    )
    response = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=_FORMATTER_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0].strip()
    return json.loads(raw)
