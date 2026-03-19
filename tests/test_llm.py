from __future__ import annotations

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
