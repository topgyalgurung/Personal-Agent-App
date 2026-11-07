import json
from unittest.mock import Mock

import pytest
import requests

from providers import ProviderUnavailable, Reply, ToolCall
from providers import ollama


def fake_response(status, body):
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps(body).encode()
    return response


TOOLS = [{
    "name": "get_tasks",
    "description": "Retrieve tasks.",
    "input_schema": {"type": "object", "properties": {}, "required": []},
}]


def test_converts_text_history_with_system_prompt_first():
    history = [
        {"role": "user", "text": "Hi"},
        {"role": "assistant", "text": "Hello!", "tool_calls": []},
    ]

    messages = ollama.to_ollama_messages(history, system="Be brief.")

    assert messages == [
        {"role": "system", "content": "Be brief."},
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"},
    ]


def test_converts_tool_call_and_tool_result():
    history = [
        {"role": "user", "text": "Tasks?"},
        {
            "role": "assistant",
            "text": "",
            "tool_calls": [
                {"id": "call_1", "name": "get_tasks", "arguments": {}},
            ],
        },
        {
            "role": "tool",
            "call_id": "call_1",
            "name": "get_tasks",
            "result": [{"title": "Reply to recruiter"}],
        },
    ]

    messages = ollama.to_ollama_messages(history, system="")

    assert messages[2] == {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"function": {"name": "get_tasks", "arguments": {}}},
        ],
    }
    assert messages[3] == {
        "role": "tool",
        "tool_name": "get_tasks",
        "content": json.dumps([{"title": "Reply to recruiter"}]),
    }


def test_parses_text_only_reply():
    reply = ollama.parse_reply({"role": "assistant", "content": "Done."})

    assert reply == Reply(text="Done.", tool_calls=[])


def test_parses_reply_with_missing_content_as_empty_text():
    reply = ollama.parse_reply({
        "role": "assistant",
        "tool_calls": [{"function": {"name": "get_tasks", "arguments": {}}}],
    })

    assert reply.text == ""


def test_parses_tool_calls_with_object_arguments():
    reply = ollama.parse_reply({
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"function": {"name": "search_notes", "arguments": {"query": "trip"}}},
            {"function": {"name": "get_tasks", "arguments": {}}},
        ],
    })

    assert reply.tool_calls == [
        ToolCall(name="search_notes", arguments={"query": "trip"}),
        ToolCall(name="get_tasks", arguments={}),
    ]


def test_parses_tool_call_arguments_sent_as_json_string():
    reply = ollama.parse_reply({
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"function": {"name": "search_notes", "arguments": '{"query": "trip"}'}},
        ],
    })

    assert reply.tool_calls[0].arguments == {"query": "trip"}


def test_parses_tool_call_with_no_arguments_key():
    reply = ollama.parse_reply({
        "role": "assistant",
        "content": "",
        "tool_calls": [{"function": {"name": "get_tasks"}}],
    })

    assert reply.tool_calls[0].arguments == {}


def test_chat_posts_to_local_ollama_with_default_model(monkeypatch):
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    post = Mock(return_value=fake_response(
        200, {"message": {"role": "assistant", "content": "Hi"}},
    ))
    monkeypatch.setattr(ollama.requests, "post", post)

    reply = ollama.OllamaAdapter().chat(
        [{"role": "user", "text": "Hello"}],
        system="Be brief.",
        tools=TOOLS,
    )

    assert reply == Reply(text="Hi", tool_calls=[])
    url = post.call_args.args[0]
    payload = post.call_args.kwargs["json"]
    assert url == "http://localhost:11434/api/chat"
    assert payload["model"] == "qwen2.5:7b"
    assert payload["stream"] is False
    assert payload["messages"][0] == {"role": "system", "content": "Be brief."}
    assert payload["tools"] == [{
        "type": "function",
        "function": {
            "name": "get_tasks",
            "description": "Retrieve tasks.",
            "parameters": TOOLS[0]["input_schema"],
        },
    }]


def test_chat_uses_model_from_environment(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.1:8b")
    post = Mock(return_value=fake_response(
        200, {"message": {"role": "assistant", "content": ""}},
    ))
    monkeypatch.setattr(ollama.requests, "post", post)

    ollama.OllamaAdapter().chat([], system="", tools=[])

    assert post.call_args.kwargs["json"]["model"] == "llama3.1:8b"


def test_adapter_reports_its_provider_name():
    assert ollama.OllamaAdapter.name == "ollama"


# --- Errors -------------------------------------------------------------


def test_connection_refused_says_how_to_start_ollama(monkeypatch):
    post = Mock(side_effect=requests.ConnectionError("refused"))
    monkeypatch.setattr(ollama.requests, "post", post)

    with pytest.raises(ProviderUnavailable) as error:
        ollama.OllamaAdapter().chat([], system="", tools=[])

    assert str(error.value) == "Ollama isn't running. Start it with: ollama serve"


def test_timeout_says_ollama_is_slow(monkeypatch):
    post = Mock(side_effect=requests.Timeout("slow"))
    monkeypatch.setattr(ollama.requests, "post", post)

    with pytest.raises(ProviderUnavailable, match="didn't answer within 60 seconds"):
        ollama.OllamaAdapter().chat([], system="", tools=[])


def test_waits_at_most_60_seconds(monkeypatch):
    post = Mock(return_value=fake_response(200, {"message": {"content": ""}}))
    monkeypatch.setattr(ollama.requests, "post", post)

    ollama.OllamaAdapter().chat([], system="", tools=[])

    assert post.call_args.kwargs["timeout"] == 60


def test_missing_model_says_how_to_pull_it(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:7b")
    post = Mock(return_value=fake_response(
        404, {"error": 'model "qwen2.5:7b" not found, try pulling it first'},
    ))
    monkeypatch.setattr(ollama.requests, "post", post)

    with pytest.raises(ProviderUnavailable) as error:
        ollama.OllamaAdapter().chat([], system="", tools=[])

    assert str(error.value) == (
        "Model qwen2.5:7b isn't downloaded. Run: ollama pull qwen2.5:7b"
    )


def test_other_http_error_reports_status(monkeypatch):
    post = Mock(return_value=fake_response(500, {"error": "boom"}))
    monkeypatch.setattr(ollama.requests, "post", post)

    with pytest.raises(ProviderUnavailable, match="status 500"):
        ollama.OllamaAdapter().chat([], system="", tools=[])


def test_malformed_argument_json_becomes_tool_call_error():
    reply = ollama.parse_reply({
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"function": {"name": "search_notes", "arguments": '{"query": "tr'}},
        ],
    })

    call = reply.tool_calls[0]
    assert call.name == "search_notes"
    assert call.arguments == {}
    assert call.error == "Tool arguments were not valid JSON."


@pytest.mark.parametrize("arguments", ['"trip"', "[1, 2]", "42"])
def test_argument_json_that_is_not_an_object_becomes_tool_call_error(arguments):
    reply = ollama.parse_reply({
        "role": "assistant",
        "content": "",
        "tool_calls": [{"function": {"name": "search_notes", "arguments": arguments}}],
    })

    assert reply.tool_calls[0].error == "Tool arguments must be a JSON object."


def test_valid_tool_call_has_no_error():
    reply = ollama.parse_reply({
        "role": "assistant",
        "content": "",
        "tool_calls": [{"function": {"name": "get_tasks", "arguments": {}}}],
    })

    assert reply.tool_calls[0].error is None
