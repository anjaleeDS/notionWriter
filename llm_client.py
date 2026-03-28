# llm_client.py
# Thin wrapper over the Anthropic SDK — conversational replies only.
# Formatting/structuring logic lives in formatter.py.
#
# send() → returns a reply string for an ongoing conversation

import os

import anthropic

_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

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
