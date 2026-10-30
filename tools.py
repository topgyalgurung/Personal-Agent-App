
"""
Initially, we'll use an in-memory list instead of a database.

can replace their implementations with PostgreSQL queries or Google Calendar API calls 
without changing the agent's tool definitions.

"""
from datetime import date, timedelta

TODAY = date.today()

tasks = [
    {
        "id": 1,
        "title": "Reply to recruiter",
        "due_date": TODAY.isoformat(),
        "completed": False,
    },
    {
        "id": 2,
        "title": "Prepare financial report",
        "due_date": (
            TODAY + timedelta(days=2)
        ).isoformat(),
        "completed": False,
    },
    {
        "id": 3,
        "title": "Practice Claude tool calling",
        "due_date": (
            TODAY + timedelta(days=7)
        ).isoformat(),
        "completed": False,
    },
]


def get_tasks():
    """Return all outstanding tasks."""
    return [
        task for task in tasks
        if not task["completed"]
    ]


def get_calendar_events():
    """Return upcoming calendar events."""
    return [
        {
            "title": "Project meeting",
            "date": (
                TODAY + timedelta(days=1)
            ).isoformat(),
        }
    ]


def create_task(title: str, due_date: str):
    """Create a new task."""
    # Validate the date before saving.
    date.fromisoformat(due_date)

    task = {
        "id": max(
            (t["id"] for t in tasks),
            default=0
        ) + 1,
        "title": title,
        "due_date": due_date,
        "completed": False,
    }

    tasks.append(task)

    return {
        "success": True,
        "task": task,
    }
