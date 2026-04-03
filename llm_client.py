# llm_client.py
# Multi-LLM wrapper — routes to Anthropic or OpenAI based on model ID.
#
# send() → returns (reply_text, usage_dict) for an ongoing conversation
# Usage dict: {"input_tokens": int, "output_tokens": int}

import os

import anthropic
import openai

from models import CLAUDE_CHAT_MODEL, CHAD_CHAT_MODEL, DEFAULT_CHAT_MODEL

_anthropic_client = None
_openai_client = None


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")
        _anthropic_client = anthropic.Anthropic(api_key=api_key)
    return _anthropic_client


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set. Add it to your .env file.")
        _openai_client = openai.OpenAI(api_key=api_key)
    return _openai_client


_CHAT_SYSTEM = (
    "You are a thoughtful conversational assistant. "
    "Engage naturally with the user — be warm, curious, and insightful. "
    "Help them think through whatever is on their mind."
)


def _is_anthropic_model(model: str) -> bool:
    return model.startswith("claude")


def send(messages: list[dict], model: str = DEFAULT_CHAT_MODEL) -> tuple[str, dict]:
    if _is_anthropic_model(model):
        client = _get_anthropic_client()
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=_CHAT_SYSTEM,
            messages=messages,
        )
        text = response.content[0].text
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return text, usage
    else:
        client = _get_openai_client()
        oai_messages = [{"role": "system", "content": _CHAT_SYSTEM}]
        oai_messages.extend(messages)
        response = client.chat.completions.create(
            model=model,
            max_tokens=1024,
            messages=oai_messages,
        )
        text = response.choices[0].message.content
        usage = {
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
        }
        return text, usage
