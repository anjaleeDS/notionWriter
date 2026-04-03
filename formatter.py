from __future__ import annotations

# formatter.py
# Converts a conversation transcript into a structured Notion entry dict.
# The LLM decides all fields; entry_type optionally overrides the type field after parsing.

import datetime
import json
from pathlib import Path

from llm_client import _get_anthropic_client, _get_openai_client, _is_anthropic_model
from models import FORMATTER_MODEL
from usage_tracker import log_usage

_FORMATTER_PROMPT = (Path(__file__).parent / "formatter_prompt.md").read_text()


def format_entry(
    messages: list[dict],
    source_model: str = "Claude",
    entry_type: str | None = None,
    session_id: str | None = None,
) -> dict:
    transcript = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
        for m in messages
    )
    prompt = (
        "The following is a full conversation between a user and an AI assistant. "
        "Generate a Notion entry based on this conversation:\n\n"
        f"{transcript}"
    )

    if _is_anthropic_model(FORMATTER_MODEL):
        client = _get_anthropic_client()
        response = client.messages.create(
            model=FORMATTER_MODEL,
            max_tokens=4096,
            system=[{
                "type": "text",
                "text": _FORMATTER_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        cache_read = getattr(response.usage, "cache_read_input_tokens", 0) or 0
    else:
        client = _get_openai_client()
        oai_messages = [
            {"role": "system", "content": _FORMATTER_PROMPT},
            {"role": "user", "content": prompt},
        ]
        response = client.chat.completions.create(
            model=FORMATTER_MODEL,
            max_tokens=4096,
            messages=oai_messages,
        )
        raw = response.choices[0].message.content.strip()
        usage = {
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
        }
        cache_read = 0

    log_usage(
        model=FORMATTER_MODEL,
        phase="formatting",
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        cache_read_tokens=cache_read,
        session_id=session_id,
    )

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
    # Always override source_model with the Python-tracked value — the LLM
    # sometimes misidentifies itself when formatting a transcript.
    entry["source_model"] = source_model
    # Inject today's date from Python so the LLM never has to guess it.
    entry["date"] = datetime.date.today().isoformat()
    return entry
