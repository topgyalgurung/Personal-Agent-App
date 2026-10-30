
from datetime import date, timedelta

from tools import (
    get_tasks,
    get_calendar_events,
    create_task,
)


def test_get_tasks():
    tasks = get_tasks()

    assert isinstance(tasks, list)
    assert all(
        not task["completed"]
        for task in tasks
    )


def test_calendar_events():
    events = get_calendar_events()

    assert isinstance(events, list)
    assert len(events) > 0


def test_create_task():
    tomorrow = (
        date.today() + timedelta(days=1)
    ).isoformat()

    result = create_task(
        "Practice Claude API",
        tomorrow,
    )

    assert result["success"] is True

    created = result["task"]

    assert created["title"] == "Practice Claude API"
    assert created["due_date"] == tomorrow

    assert any(
        task["id"] == created["id"]
        for task in get_tasks()
    )
