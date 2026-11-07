from fastapi.testclient import TestClient

import server
import tool_dispatch
from agent_core import Session
from providers import ProviderUnavailable, Reply, ToolCall


class FakeAdapter:
    name = "fake"

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    def chat(self, history, *, system, tools):
        self.calls.append([dict(m) for m in history])
        reply = self.replies.pop(0)

        if isinstance(reply, Exception):
            raise reply

        return reply


def make_client(*replies):
    adapter = FakeAdapter(*replies)
    client = TestClient(server.create_app(Session(adapter)))

    return client, adapter


def test_chat_returns_the_answer():
    client, _ = make_client(Reply(text="Hello!"))

    response = client.post("/api/chat", json={"message": "Hi"})

    assert response.status_code == 200
    assert response.json() == {"text": "Hello!", "error": None, "tools": []}


def test_consecutive_calls_share_memory():
    client, adapter = make_client(Reply(text="One"), Reply(text="Two"))

    client.post("/api/chat", json={"message": "first"})
    client.post("/api/chat", json={"message": "second"})

    roles = [m["role"] for m in adapter.calls[1]]
    assert roles == ["user", "assistant", "user"]


def test_empty_or_blank_message_is_rejected():
    client, adapter = make_client()

    assert client.post("/api/chat", json={"message": ""}).status_code == 422
    assert client.post("/api/chat", json={"message": "   "}).status_code == 422
    assert client.post("/api/chat", json={}).status_code == 422
    assert adapter.calls == []


def test_agent_errors_come_back_in_the_body_not_as_a_500():
    client, _ = make_client(ProviderUnavailable("Ollama isn't running."))

    response = client.post("/api/chat", json={"message": "Hi"})

    assert response.status_code == 200
    assert response.json()["error"] == "Ollama isn't running."
    assert response.json()["text"] == ""


def test_unexpected_failures_are_a_friendly_error_not_a_500():
    client, _ = make_client(RuntimeError("boom"))

    response = client.post("/api/chat", json={"message": "Hi"})

    assert response.status_code == 200
    assert "went wrong" in response.json()["error"]
    assert "boom" not in response.json()["error"]


def test_tool_names_are_reported(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:7b")
    monkeypatch.setitem(tool_dispatch.REGISTRY, "list_events", lambda **kw: [])
    client, _ = make_client(
        Reply(text="", tool_calls=[ToolCall(name="list_events", arguments={})]),
        Reply(text="Nothing today."),
    )

    response = client.post("/api/chat", json={"message": "today?"})

    assert response.json()["tools"] == ["list_events"]


def test_home_serves_the_chat_page():
    client, _ = make_client()

    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "/api/chat" in response.text


def test_server_only_listens_on_localhost():
    assert server.HOST == "127.0.0.1"
