
"""
Initially, we'll use an in-memory list instead of a database.

can replace their implementations with PostgreSQL queries or Google Calendar API calls 
without changing the agent's tool definitions.

"""
from datetime import date, datetime, timedelta

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

def add_duration_to_datetime(
    datetime_str, duration=0, unit="days", input_format="%Y-%m-%d"
):
    date = datetime.strptime(datetime_str, input_format)

    if unit == "seconds":
        new_date = date + timedelta(seconds=duration)
    elif unit == "minutes":
        new_date = date + timedelta(minutes=duration)
    elif unit == "hours":
        new_date = date + timedelta(hours=duration)
    elif unit == "days":
        new_date = date + timedelta(days=duration)
    elif unit == "weeks":
        new_date = date + timedelta(weeks=duration)
    elif unit == "months":
        month = date.month + duration
        year = date.year + month // 12
        month = month % 12
        if month == 0:
            month = 12
            year -= 1
        day = min(
            date.day,
            [
                31,
                29
                if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
                else 28,
                31,
                30,
                31,
                30,
                31,
                31,
                30,
                31,
                30,
                31,
            ][month - 1],
        )
        new_date = date.replace(year=year, month=month, day=day)
    elif unit == "years":
        new_date = date.replace(year=date.year + duration)
    else:
        raise ValueError(f"Unsupported time unit: {unit}")

    return new_date.strftime("%A, %B %d, %Y %I:%M:%S %p")


def set_reminder(content, timestamp):
    print(
        f"----\nSetting the following reminder for {timestamp}:\n{content}\n----"
    )

from integrations.apple_notes import (
    list_notes,
    search_notes,
    read_note,
)