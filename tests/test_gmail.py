import base64

import pytest

from integrations import gmail
from integrations.gmail import MAX_BODY_CHARS, read_email, search_emails


def b64(text):
    return base64.urlsafe_b64encode(text.encode()).decode()


def headers(**values):
    return [{"name": k.replace("_", "-"), "value": v} for k, v in values.items()]


class Service:
    """Fake Gmail client: service.users().messages().list/get(...).execute()."""

    def __init__(self, data):
        self.data = data
        self.list_params = None
        self.get_calls = []
        self._pending = None

    def users(self):
        return self

    def messages(self):
        return self

    def list(self, **params):
        self.list_params = params
        ids = [{"id": i} for i in self.data]
        self._pending = {"messages": ids} if ids else {}
        return self

    def get(self, **params):
        self.get_calls.append(params)
        self._pending = self.data[params["id"]]
        return self

    def execute(self):
        return self._pending


def message(id, payload, snippet="snip", **hdrs):
    return {
        "id": id,
        "snippet": snippet,
        "payload": {
            "headers": headers(From="Ann <ann@x.com>", Subject="Hi", Date="Wed", **hdrs),
            **payload,
        },
    }


def test_search_returns_metadata_only():
    service = Service({"m1": message("m1", {}, snippet="Lunch?")})

    results = search_emails("is:unread", service=service)

    assert results == [{
        "id": "m1",
        "from": "Ann <ann@x.com>",
        "subject": "Hi",
        "date": "Wed",
        "snippet": "Lunch?",
    }]
    assert service.list_params["q"] == "is:unread"
    assert service.get_calls[0]["format"] == "metadata"


def test_search_limit_is_applied_and_capped():
    service = Service({})

    search_emails("x", limit=500, service=service)

    assert service.list_params["maxResults"] == 25


def test_search_with_no_results_is_an_empty_list():
    assert search_emails("nothing", service=Service({})) == []


def test_read_returns_plain_text_body():
    payload = {"mimeType": "text/plain", "body": {"data": b64("Hello there")}}
    service = Service({"m1": message("m1", payload)})

    result = read_email("m1", service=service)

    assert result["body"] == "Hello there"
    assert result["subject"] == "Hi"
    assert result["truncated"] is False


def test_read_strips_html_when_there_is_no_plain_part():
    html = "<html><style>p{}</style><body><p>Hello <b>Bob</b></p><script>x()</script></body></html>"
    payload = {"mimeType": "text/html", "body": {"data": b64(html)}}
    service = Service({"m1": message("m1", payload)})

    assert read_email("m1", service=service)["body"] == "Hello Bob"


def test_read_prefers_plain_part_in_multipart_messages():
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {"mimeType": "text/html", "body": {"data": b64("<p>HTML version</p>")}},
            {"mimeType": "text/plain", "body": {"data": b64("Plain version")}},
        ],
    }
    service = Service({"m1": message("m1", payload)})

    assert read_email("m1", service=service)["body"] == "Plain version"


def test_read_finds_text_in_nested_parts_and_skips_attachments():
    payload = {
        "mimeType": "multipart/mixed",
        "parts": [
            {
                "mimeType": "multipart/alternative",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": b64("Deep text")}},
                ],
            },
            {
                "mimeType": "application/pdf",
                "filename": "a.pdf",
                "body": {"attachmentId": "att"},
            },
        ],
    }
    service = Service({"m1": message("m1", payload)})

    assert read_email("m1", service=service)["body"] == "Deep text"


def test_read_truncates_long_bodies_with_a_marker():
    payload = {"mimeType": "text/plain", "body": {"data": b64("a" * 10000)}}
    service = Service({"m1": message("m1", payload)})

    result = read_email("m1", service=service)

    assert result["truncated"] is True
    assert result["body"].startswith("a" * MAX_BODY_CHARS)
    assert result["body"].endswith("[truncated]")
    assert len(result["body"]) < MAX_BODY_CHARS + 50


def test_read_with_no_text_says_so():
    service = Service({"m1": message("m1", {"mimeType": "image/png", "body": {}})})

    assert read_email("m1", service=service)["body"] == "(no readable text)"


def test_read_requires_an_id():
    with pytest.raises(ValueError, match="id"):
        read_email("", service=Service({}))


def test_builds_the_service_from_saved_credentials(monkeypatch):
    built = {}
    monkeypatch.setattr(gmail, "get_credentials", lambda: "creds")
    monkeypatch.setattr(
        gmail,
        "build",
        lambda name, version, credentials, cache_discovery: built.update(
            name=name, version=version
        ) or Service({}),
    )

    search_emails("x")

    assert built == {"name": "gmail", "version": "v1"}
