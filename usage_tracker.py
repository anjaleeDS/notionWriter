from __future__ import annotations

# usage_tracker.py
# Tracks per-call token usage and estimated cost.
# Logs to usage_log.json and provides budget warning checks.

import datetime
import json
import os
from pathlib import Path

from models import MODEL_PRICING

_LOG_FILE = Path(__file__).parent / "usage_log.json"
_MONTHLY_BUDGET = float(os.getenv("MONTHLY_BUDGET_USD", "10.0"))

# Budget warning thresholds (fraction of monthly budget)
_WARN_THRESHOLDS = [0.50, 0.80, 0.95]
# Track which thresholds have already fired this month (in-memory, resets on restart)
_fired_warnings: set[float] = set()
_fired_month: str = ""


def _load_log() -> list[dict]:
    if _LOG_FILE.exists():
        try:
            return json.loads(_LOG_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return []
    return []


def _save_log(entries: list[dict]) -> None:
    _LOG_FILE.write_text(json.dumps(entries, indent=2))


def estimate_cost(model: str, input_tokens: int, output_tokens: int, cache_read_tokens: int = 0) -> float:
    pricing = MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
    cost = (input_tokens * pricing["input"] / 1_000_000
            + output_tokens * pricing["output"] / 1_000_000)
    if cache_read_tokens and "cache_read" in pricing:
        cost += cache_read_tokens * pricing["cache_read"] / 1_000_000
    return round(cost, 6)


def log_usage(
    model: str,
    phase: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    notion_page_id: str | None = None,
    session_id: str | None = None,
) -> dict:
    cost = estimate_cost(model, input_tokens, output_tokens, cache_read_tokens)
    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "model": model,
        "phase": phase,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_tokens": cache_read_tokens,
        "estimated_cost_usd": cost,
        "notion_page_id": notion_page_id,
        "session_id": session_id,
    }
    log = _load_log()
    log.append(entry)
    _save_log(log)
    return entry


def link_session_to_page(session_id: str, notion_page_id: str) -> None:
    """After /save, update all log entries for this session with the Notion page ID."""
    log = _load_log()
    changed = False
    for entry in log:
        if entry.get("session_id") == session_id and entry.get("notion_page_id") is None:
            entry["notion_page_id"] = notion_page_id
            changed = True
    if changed:
        _save_log(log)


def get_monthly_total() -> dict:
    """Returns current month's usage summary."""
    now = datetime.datetime.now(datetime.timezone.utc)
    month_prefix = now.strftime("%Y-%m")
    log = _load_log()

    total_cost = 0.0
    total_input = 0
    total_output = 0
    by_model: dict[str, float] = {}
    entry_count = 0

    for entry in log:
        if entry["timestamp"].startswith(month_prefix):
            cost = entry.get("estimated_cost_usd", 0.0)
            total_cost += cost
            total_input += entry.get("input_tokens", 0)
            total_output += entry.get("output_tokens", 0)
            model = entry.get("model", "unknown")
            by_model[model] = by_model.get(model, 0.0) + cost
            entry_count += 1

    return {
        "month": month_prefix,
        "total_cost_usd": round(total_cost, 4),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "by_model": {k: round(v, 4) for k, v in by_model.items()},
        "api_calls": entry_count,
        "budget_usd": _MONTHLY_BUDGET,
        "budget_used_pct": round(total_cost / _MONTHLY_BUDGET * 100, 1) if _MONTHLY_BUDGET > 0 else 0.0,
    }


def check_budget_warnings() -> str | None:
    """Returns a warning message if a new budget threshold has been crossed, else None."""
    global _fired_warnings, _fired_month

    now = datetime.datetime.now(datetime.timezone.utc)
    current_month = now.strftime("%Y-%m")

    # Reset fired warnings on new month
    if _fired_month != current_month:
        _fired_warnings = set()
        _fired_month = current_month

    summary = get_monthly_total()
    fraction = summary["total_cost_usd"] / _MONTHLY_BUDGET if _MONTHLY_BUDGET > 0 else 0.0

    for threshold in _WARN_THRESHOLDS:
        if fraction >= threshold and threshold not in _fired_warnings:
            _fired_warnings.add(threshold)
            pct = int(threshold * 100)
            return (
                f"⚠️ Budget alert: you've used {pct}% of your ${_MONTHLY_BUDGET:.2f} monthly budget "
                f"(${summary['total_cost_usd']:.4f} spent, {summary['api_calls']} API calls this month)."
            )
    return None
