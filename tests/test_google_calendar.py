from datetime import date, datetime

import pytest

from integrations import google_calendar
from integrations.google_calendar import list_events


class FakeService:
    def __init__(self, items):
        self.items = items
        self.params = None

    def events(self):
        return self

    def list(self, **params):
        self.params = params
        return self

    def execute(self):
        return {"items": self.items}


def timed(summary, start, end, **extra):
    return {
        "summary": summary,
        "start": {"dateTime": start},
        "end": {"dateTime": end},
        **extra,
    }


def test_returns_title_times_location_and_attendee_count():
    service = FakeService([
        timed(
            "Standup",
            "2026-11-05T09:00:00-05:00",
            "2026-11-05T09:15:00-05:00",
            location="Zoom",
            attendees=[{"email": "a@x.com"}, {"email": "b@x.com"}],
        )
    ])

    events = list_events("2026-11-05", service=service)

    assert events == [{
        "title": "Standup",
        "start": "2026-11-05T09:00:00-05:00",
        "end": "2026-11-05T09:15:00-05:00",
        "all_day": False,
        "location": "Zoom",
        "attendees": 2,
    }]


def test_all_day_events_use_dates_and_are_flagged():
    service = FakeService([{
        "summary": "Holiday",
        "start": {"date": "2026-11-05"},
        "end": {"date": "2026-11-06"},
    }])

    event = list_events("2026-11-05", service=service)[0]

    assert event["all_day"] is True
    assert event["start"] == "2026-11-05"
    assert event["location"] == ""
    assert event["attendees"] == 0


def test_untitled_and_cancelled_events():
    service = FakeService([
        {"start": {"date": "2026-11-05"}, "end": {"date": "2026-11-06"}},
        {
            "summary": "Gone",
            "status": "cancelled",
            "start": {"date": "2026-11-05"},
            "end": {"date": "2026-11-06"},
        },
    ])

    events = list_events("2026-11-05", service=service)

    assert [e["title"] for e in events] == ["(no title)"]


def test_asks_google_for_ordered_single_events_in_the_local_day_range():
    service = FakeService([])

    list_events("2026-11-05", "2026-11-06", service=service)

    params = service.params
    assert params["calendarId"] == "primary"
    assert params["singleEvents"] is True
    assert params["orderBy"] == "startTime"
    start = datetime.fromisoformat(params["timeMin"])
    end = datetime.fromisoformat(params["timeMax"])
    assert start.date() == date(2026, 11, 5) and start.hour == 0
    assert end.date() == date(2026, 11, 7) and end.hour == 0
    assert start.utcoffset() is not None


def test_defaults_to_today():
    service = FakeService([])

    list_events(service=service)

    start = datetime.fromisoformat(service.params["timeMin"])
    assert start.date() == date.today()


@pytest.mark.parametrize("start, end", [
    ("tomorrow", None),
    ("2026-11-05", "soon"),
    ("2026-11-06", "2026-11-05"),
])
def test_bad_dates_raise_a_clear_error(start, end):
    with pytest.raises(ValueError, match="YYYY-MM-DD|before"):
        list_events(start, end, service=FakeService([]))


def test_builds_the_service_from_saved_credentials(monkeypatch):
    built = {}
    monkeypatch.setattr(google_calendar, "get_credentials", lambda: "creds")
    monkeypatch.setattr(
        google_calendar,
        "build",
        lambda name, version, credentials, cache_discovery: built.update(
            name=name, version=version, credentials=credentials
        ) or FakeService([]),
    )

    list_events("2026-11-05")

    assert built == {"name": "calendar", "version": "v3", "credentials": "creds"}
