# formatter.py
# Converts a conversation transcript into a structured Notion entry dict.
# The LLM decides all fields; entry_type optionally overrides the type field after parsing.

import json
from pathlib import Path

from llm_client import _client, CLAUDE_MODEL

_FORMATTER_PROMPT = (Path(__file__).parent / "formatter_prompt.md").read_text()


def format_entry(messages: list[dict], source_model: str = "Claude", entry_type: str | None = None) -> dict:
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
        max_tokens=4096,
        system=_FORMATTER_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    print(f"[format_entry] raw response: {repr(raw[:200])}")
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0].strip()
    # strip any prose preamble before the JSON object
    brace = raw.find("{")
    if brace > 0:
        raw = raw[brace:]
    entry = json.loads(raw)
    if entry_type is not None:
        entry["type"] = entry_type
    return entry
