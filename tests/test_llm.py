from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest


def _mock_chat_response(content: str):
    """Create a mock OpenAI response with the given content."""
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@pytest.fixture(autouse=True)
def _reset_client():
    """Reset the module-level singleton before each test."""
    import engine.llm as llm_mod
    llm_mod._client = None
    yield
    llm_mod._client = None


def _call_chat_json(raw_text: str):
    """Patch the client and call chat_json, returning the parsed result."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_chat_response(raw_text)

    with patch("engine.llm.get_client", return_value=mock_client):
        from engine.llm import chat_json
        return chat_json("test prompt")


class TestChatJson:
    def test_clean_json_array(self):
        result = _call_chat_json('[{"a": 1}]')
        assert result == [{"a": 1}]

    def test_markdown_fenced_json(self):
        result = _call_chat_json('```json\n[{"a": 1}]\n```')
        assert result == [{"a": 1}]

    def test_text_before_json(self):
        result = _call_chat_json('Here is the result: [{"a": 1}]')
        assert result == [{"a": 1}]

    def test_truncated_array_salvage(self):
        # Truncated mid-object — boundary finder extracts the first complete object as a dict
        result = _call_chat_json('[{"a": 1}, {"b": 2')
        assert result == {"a": 1}

    def test_truncated_array_salvage_multiple_complete(self):
        # Truncated after complete objects — salvage via last "}," returns all before it
        result = _call_chat_json('[{"a": 1},{"b": 2},{"c": 3')
        assert result == [{"a": 1}, {"b": 2}]

    def test_truncated_with_trailing_comma(self):
        result = _call_chat_json('[{"a": 1}, {"b": 2},')
        assert result == [{"a": 1}, {"b": 2}]

    def test_empty_response_raises(self):
        with pytest.raises(ValueError, match="empty"):
            _call_chat_json("")

    def test_no_json_raises(self):
        with pytest.raises(ValueError, match="Could not parse"):
            _call_chat_json("I don't know")

    def test_json_object(self):
        result = _call_chat_json('{"signals": [{"a": 1}]}')
        assert result == {"signals": [{"a": 1}]}


class TestSanitizeError:
    def test_html_error_stripped(self):
        from engine.llm import _sanitize_error
        e = Exception("<html><body><h1>502 Bad Gateway</h1></body></html>")
        result = _sanitize_error(e)
        assert "<html" not in result
        assert "502 Bad Gateway" in result

    def test_plain_error_unchanged(self):
        from engine.llm import _sanitize_error
        e = RuntimeError("Connection timed out")
        assert _sanitize_error(e) == "Connection timed out"

    def test_empty_html_body_returns_type_name(self):
        from engine.llm import _sanitize_error
        e = ValueError("<html>   </html>")
        result = _sanitize_error(e)
        assert result == "ValueError"


class TestGetClient:
    def test_missing_api_key_raises(self):
        from engine.llm import get_client
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
                get_client()

    def test_client_cached(self):
        from engine.llm import get_client
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            c1 = get_client()
            c2 = get_client()
            assert c1 is c2


class TestChat:
    def test_success_first_attempt(self):
        from engine.llm import chat
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_chat_response("hello")
        with patch("engine.llm.get_client", return_value=mock_client):
            result = chat("test")
        assert result == "hello"
        assert mock_client.chat.completions.create.call_count == 1

    def test_retry_on_failure_then_succeed(self):
        from engine.llm import chat
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            RuntimeError("fail"),
            _mock_chat_response("ok"),
        ]
        with patch("engine.llm.get_client", return_value=mock_client), \
             patch("time.sleep"):
            result = chat("test")
        assert result == "ok"

    def test_all_retries_exhausted_raises(self):
        from engine.llm import chat
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("fail")
        with patch("engine.llm.get_client", return_value=mock_client), \
             patch("time.sleep"):
            with pytest.raises(RuntimeError, match="fail"):
                chat("test")

    def test_on_retry_callback_invoked(self):
        from engine.llm import chat
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            RuntimeError("oops"),
            _mock_chat_response("ok"),
        ]
        callback = MagicMock()
        with patch("engine.llm.get_client", return_value=mock_client), \
             patch("time.sleep"):
            chat("test", on_retry=callback)
        callback.assert_called_once()
        args = callback.call_args[0]
        assert args[0] == 1  # attempt
        assert args[1] == 2  # max_retries

    def test_empty_choices_raises(self):
        from engine.llm import chat
        mock_client = MagicMock()
        resp = MagicMock()
        resp.choices = []
        mock_client.chat.completions.create.return_value = resp
        with patch("engine.llm.get_client", return_value=mock_client), \
             patch("time.sleep"):
            with pytest.raises(ValueError, match="no choices"):
                chat("test")
