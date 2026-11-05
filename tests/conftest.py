import pytest

import tool_dispatch


@pytest.fixture
def stub_tools(monkeypatch):
    """Harmless tools for tests of the dispatch/session machinery."""
    monkeypatch.setitem(tool_dispatch.REGISTRY, "get_tasks", lambda: [])
    monkeypatch.setitem(tool_dispatch.REGISTRY, "get_calendar_events", lambda: [])
    monkeypatch.setitem(
        tool_dispatch.REGISTRY,
        "create_task",
        lambda title, due_date: {"success": True, "task": {"title": title}},
    )
