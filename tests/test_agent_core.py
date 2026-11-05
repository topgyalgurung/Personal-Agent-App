import copy
from datetime import date

from agent_core import Session, Turn
from providers import Reply, ToolCall
from schemas import TOOLS


class FakeAdapter:
    """Returns scripted replies and records what it was sent."""

    name = "ollama"

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    def chat(self, history, *, system, tools):
        self.calls.append({
            "history": copy.deepcopy(history),
            "system": system,
            "tools": tools,
        })
        return self.replies.pop(0)


def make_session(*replies):
    adapter = FakeAdapter(*replies)
    session = Session(adapter, system_prompt=lambda: "SYSTEM")
    return session, adapter


def test_plain_answer_returns_finished_turn():
    session, _ = make_session(Reply(text="Hello!"))

    turn = session.send("Hi")

    assert isinstance(turn, Turn)
    assert turn.provider == "ollama"
    assert turn.text == "Hello!"
    assert turn.tool_calls == []
    assert turn.pending is None
    assert turn.error is None


def test_sends_system_prompt_and_tool_schemas():
    session, adapter = make_session(Reply(text="Hello!"))

    session.send("Hi")

    assert adapter.calls[0]["system"] == "SYSTEM"
    assert adapter.calls[0]["tools"] == TOOLS


def test_one_tool_call_then_answer():
    session, adapter = make_session(
        Reply(text="", tool_calls=[ToolCall(name="get_tasks", arguments={})]),
        Reply(text="You have 3 tasks."),
    )

    turn = session.send("What are my tasks?")

    assert turn.text == "You have 3 tasks."
    assert len(turn.tool_calls) == 1
    record = turn.tool_calls[0]
    assert record.name == "get_tasks"
    assert record.arguments == {}
    assert isinstance(record.result, list)

    second_history = adapter.calls[1]["history"]
    assistant, tool = second_history[-2], second_history[-1]
    assert assistant["tool_calls"][0]["id"] == record.id
    assert tool == {
        "role": "tool",
        "call_id": record.id,
        "name": "get_tasks",
        "result": record.result,
    }


def test_several_tool_calls_in_one_reply_run_in_order():
    due = date.today().isoformat()
    session, adapter = make_session(
        Reply(text="", tool_calls=[
            ToolCall(name="get_tasks", arguments={}),
            ToolCall(name="create_task", arguments={"title": "Call mom", "due_date": due}),
        ]),
        Reply(text="Done."),
    )

    turn = session.send("Show tasks and add one")

    assert [r.name for r in turn.tool_calls] == ["get_tasks", "create_task"]
    assert turn.tool_calls[1].result["task"]["title"] == "Call mom"
    tool_messages = [m for m in adapter.calls[1]["history"] if m["role"] == "tool"]
    assert [m["name"] for m in tool_messages] == ["get_tasks", "create_task"]


def test_tool_calls_across_several_rounds_are_all_recorded():
    session, _ = make_session(
        Reply(text="", tool_calls=[ToolCall(name="get_tasks", arguments={})]),
        Reply(text="", tool_calls=[ToolCall(name="get_calendar_events", arguments={})]),
        Reply(text="Here is your day."),
    )

    turn = session.send("Plan my day")

    assert [r.name for r in turn.tool_calls] == ["get_tasks", "get_calendar_events"]
    assert turn.text == "Here is your day."


def test_failing_tool_returns_error_result_and_turn_finishes(monkeypatch):
    monkeypatch.setenv("APPLE_NOTES_ENABLED", "0")
    session, adapter = make_session(
        Reply(text="", tool_calls=[ToolCall(name="list_notes", arguments={})]),
        Reply(text="Notes access is off."),
    )

    turn = session.send("List my notes")

    assert turn.text == "Notes access is off."
    assert turn.tool_calls[0].result == {
        "success": False,
        "error": "Apple Notes access is disabled.",
    }
    assert adapter.calls[1]["history"][-1]["result"]["success"] is False


def test_second_send_includes_first_exchange():
    session, adapter = make_session(
        Reply(text="Paris trip notes found."),
        Reply(text="Budget is $2,000."),
    )

    session.send("What's in my trip notes?")
    session.send("And the budget?")

    assert adapter.calls[1]["history"] == [
        {"role": "user", "text": "What's in my trip notes?"},
        {"role": "assistant", "text": "Paris trip notes found.", "tool_calls": []},
        {"role": "user", "text": "And the budget?"},
    ]


def test_turn_lists_only_its_own_tool_calls():
    session, _ = make_session(
        Reply(text="", tool_calls=[ToolCall(name="get_tasks", arguments={})]),
        Reply(text="3 tasks."),
        Reply(text="You're welcome."),
    )

    session.send("Tasks?")
    second = session.send("Thanks")

    assert second.tool_calls == []


def test_tool_call_ids_are_unique_across_turns():
    session, _ = make_session(
        Reply(text="", tool_calls=[
            ToolCall(name="get_tasks", arguments={}),
            ToolCall(name="get_tasks", arguments={}),
        ]),
        Reply(text="Done."),
        Reply(text="", tool_calls=[ToolCall(name="get_tasks", arguments={})]),
        Reply(text="Done again."),
    )

    first = session.send("Tasks twice")
    second = session.send("Tasks again")

    ids = [r.id for r in first.tool_calls + second.tool_calls]
    assert len(ids) == len(set(ids)) == 3
    assert all(ids)


def test_keeps_tool_call_id_supplied_by_provider():
    session, _ = make_session(
        Reply(text="", tool_calls=[
            ToolCall(name="get_tasks", arguments={}, id="toolu_abc"),
        ]),
        Reply(text="Done."),
    )

    turn = session.send("Tasks?")

    assert turn.tool_calls[0].id == "toolu_abc"


def test_each_turn_gets_a_unique_id():
    session, _ = make_session(Reply(text="One"), Reply(text="Two"))

    first = session.send("1")
    second = session.send("2")

    assert first.id and second.id
    assert first.id != second.id


def test_defaults_to_ollama_adapter():
    session = Session()

    assert session.adapter.name == "ollama"
