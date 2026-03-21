from __future__ import annotations

import json
import logging
import os
import re
import time

from typing import Callable

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

_client: OpenAI | None = None


def _sanitize_error(e: Exception) -> str:
    """Strip HTML from error messages (e.g., nginx 502 pages)."""
    msg = str(e)
    if "<html" in msg.lower():
        cleaned = re.sub(r"<[^>]+>", "", msg).strip()
        # Collapse whitespace
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned or type(e).__name__
    return msg


MAX_RETRIES = 2
RETRY_BACKOFF = [5, 10]  # seconds between retries
REQUEST_TIMEOUT = 60  # seconds


def get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not set in environment")
        _client = OpenAI(api_key=api_key, base_url=BASE_URL, timeout=REQUEST_TIMEOUT)
    return _client


def chat(
    prompt: str,
    system: str = "You are a helpful policy analyst.",
    max_tokens: int = 4096,
    on_retry: Callable[[int, int, str], None] | None = None,
) -> str:
    """Call the LLM with automatic retries.

    Args:
        on_retry: Optional callback(attempt, max_retries, error_message)
            called before each retry sleep.
    """
    client = get_client()
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=max_tokens,
            )
            if not response.choices:
                raise ValueError("LLM returned response with no choices")
            choice = response.choices[0]
            if getattr(choice, "finish_reason", None) == "length":
                logging.warning(
                    "LLM response truncated (finish_reason=length) — "
                    "output may be incomplete. Consider raising max_tokens."
                )
            return choice.message.content
        except Exception as e:
            last_error = e
            error_msg = _sanitize_error(e)
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
                logging.warning(
                    "LLM request failed (attempt %d/%d), retrying in %ds: %s",
                    attempt + 1, MAX_RETRIES, wait, error_msg,
                )
                if on_retry:
                    on_retry(attempt + 1, MAX_RETRIES, error_msg)
                time.sleep(wait)

    if last_error is None:
        raise RuntimeError("LLM chat() called with MAX_RETRIES=0")
    raise last_error


def _find_last_complete_object(text: str, start: int) -> int:
    """Walk *text* from *start* tracking ``{``/``}`` depth (respecting JSON strings).

    Returns the index of the closing ``}`` of the last top-level object that
    is fully closed (depth returns to 0), or ``-1`` if none is found.
    """
    depth = 0
    in_string = False
    escape = False
    last_complete_end = -1

    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            if in_string:
                escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                last_complete_end = i
    return last_complete_end


def _repair_truncated_json(text: str) -> str:
    """Attempt to make truncated JSON valid by closing open strings and containers."""
    stack: list[str] = []
    in_string = False
    escape = False

    for ch in text:
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in ("{", "["):
            stack.append(ch)
        elif ch == "}":
            if stack and stack[-1] == "{":
                stack.pop()
        elif ch == "]":
            if stack and stack[-1] == "[":
                stack.pop()

    suffix = ""
    if in_string:
        suffix += '"'
    for bracket in reversed(stack):
        suffix += "}" if bracket == "{" else "]"
    return text + suffix


def chat_json(
    prompt: str,
    system: str = "You are a helpful policy analyst. Respond with valid JSON only — no markdown fences, no explanation, just the JSON array or object. Output minified/compact JSON with no extra whitespace or newlines.",
    max_tokens: int = 4096,
    on_retry: Callable[[int, int, str], None] | None = None,
) -> list | dict:
    raw = chat(prompt, system, max_tokens=max_tokens, on_retry=on_retry)
    if not raw or not raw.strip():
        raise ValueError("LLM returned empty response")

    text = raw.strip()

    # Strip markdown code fences if present
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find JSON array or object boundaries
    for start_char, end_char in [("[", "]"), ("{", "}")]:
        start = text.find(start_char)
        if start == -1:
            continue
        end = text.rfind(end_char)
        if end == -1 or end <= start:
            continue
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            continue

    # Truncated JSON array — try to salvage complete top-level objects
    start = text.find("[")
    if start != -1:
        last_complete_end = _find_last_complete_object(text, start + 1)
        if last_complete_end != -1:
            salvaged = text[start:last_complete_end + 1] + "]"
            try:
                return json.loads(salvaged)
            except json.JSONDecodeError:
                pass

    # Last resort — repair truncated JSON by closing open strings/containers
    repaired = _repair_truncated_json(text)
    try:
        result = json.loads(repaired)
        logging.warning(
            "Repaired truncated JSON (len=%d) by closing open containers", len(text)
        )
        return result
    except json.JSONDecodeError:
        pass

    raise ValueError(f"Could not parse JSON from LLM response: {text[:300]}")
