# app.py
# FastAPI server — receives Telegram webhook updates, exposes a health check.
# On startup, registers the webhook URL with Telegram so messages are forwarded here.
#
# Required env vars:
#   TELEGRAM_BOT_TOKEN  — from BotFather
#   WEBHOOK_URL         — the public Railway URL (e.g. https://your-app.up.railway.app)
#   ANTHROPIC_API_KEY   — Claude API key
#   NOTION_TOKEN        — Notion integration token
#   NOTION_DATABASE_ID  — Notion database ID

import os

import httpx
from fastapi import FastAPI, Request

from bot import handle_update

app = FastAPI()

_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
_WEBHOOK_URL = os.getenv("WEBHOOK_URL")


@app.on_event("startup")
async def register_webhook() -> None:
    if not _TOKEN or not _WEBHOOK_URL:
        print("Warning: TELEGRAM_BOT_TOKEN or WEBHOOK_URL not set — skipping webhook registration")
        return
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.telegram.org/bot{_TOKEN}/setWebhook",
            params={"url": f"{_WEBHOOK_URL}/webhook"},
        )
        print("Webhook registration:", resp.json())


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    await handle_update(data)
    return {"ok": True}
