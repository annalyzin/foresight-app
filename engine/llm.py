from __future__ import annotations

import json
import logging
import os
import re
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = os.getenv("LITELLM_MODEL", "claude-sonnet-4-6-asia-southeast1")
BASE_URL = os.getenv("LITELLM_BASE_URL", "https://litellm-stg.aip.gov.sg")

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
        api_key = os.getenv("LITELLM_API_KEY")
        if not api_key:
            raise ValueError("LITELLM_API_KEY not set in environment")
        _client = OpenAI(api_key=api_key, base_url=BASE_URL, timeout=REQUEST_TIMEOUT)
    return _client


def chat(
    prompt: str,
    system: str = "You are a helpful policy analyst.",
    max_tokens: int = 4096,
    on_retry: "Callable[[int, int, str], None] | None" = None,
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
            return response.choices[0].message.content
        except Exception as e:
            last_error = e
            error_msg = _sanitize_error(e)
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF[attempt]
                logging.warning(
                    "LLM request failed (attempt %d/%d), retrying in %ds: %s",
                    attempt + 1, MAX_RETRIES, wait, error_msg,
                )
                if on_retry:
                    on_retry(attempt + 1, MAX_RETRIES, error_msg)
                time.sleep(wait)

    raise last_error


def chat_json(
    prompt: str,
    system: str = "You are a helpful policy analyst. Respond with valid JSON only — no markdown fences, no explanation, just the JSON array or object.",
    max_tokens: int = 4096,
    on_retry: "Callable[[int, int, str], None] | None" = None,
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

    # Truncated JSON array — try to salvage complete objects
    start = text.find("[")
    if start != -1:
        partial = text[start:]
        # Find the last complete object by looking for the last "},"  or "}" before truncation
        last_complete = partial.rfind("},")
        if last_complete != -1:
            salvaged = partial[:last_complete + 1] + "]"
            try:
                return json.loads(salvaged)
            except json.JSONDecodeError:
                pass
        # Try finding last complete object ending with "}"
        last_obj = partial.rfind("}")
        if last_obj != -1:
            salvaged = partial[:last_obj + 1] + "]"
            try:
                return json.loads(salvaged)
            except json.JSONDecodeError:
                pass

    raise ValueError(f"Could not parse JSON from LLM response: {text[:300]}")
