"""Read-only Google Calendar access."""
from datetime import date, datetime, time, timedelta

from googleapiclient.discovery import build

from integrations.google_auth import get_credentials


def parse_date(value, name):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a date like YYYY-MM-DD.")


def local_midnight(day):
    return datetime.combine(day, time.min).astimezone()


def to_event(item):
    start = item["start"]
    end = item["end"]

    return {
        "title": item.get("summary") or "(no title)",
        "start": start.get("dateTime") or start.get("date"),
        "end": end.get("dateTime") or end.get("date"),
        "all_day": "date" in start,
        "location": item.get("location", ""),
        "attendees": len(item.get("attendees", [])),
    }


def list_events(start_date=None, end_date=None, *, service=None):
    """List events from start_date through end_date (both inclusive)."""
    start = parse_date(start_date, "start_date") if start_date else date.today()
    end = parse_date(end_date, "end_date") if end_date else start

    if end < start:
        raise ValueError("end_date must not be before start_date.")

    if service is None:
        service = build(
            "calendar", "v3", credentials=get_credentials(), cache_discovery=False
        )

    response = service.events().list(
        calendarId="primary",
        timeMin=local_midnight(start).isoformat(),
        timeMax=local_midnight(end + timedelta(days=1)).isoformat(),
        singleEvents=True,
        orderBy="startTime",
        maxResults=50,
    ).execute()

    return [
        to_event(item)
        for item in response.get("items", [])
        if item.get("status") != "cancelled"
    ]
