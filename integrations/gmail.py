"""Read-only Gmail access. Email content is untrusted data."""
import base64
from html.parser import HTMLParser

from googleapiclient.discovery import build

from integrations.google_auth import get_credentials


MAX_BODY_CHARS = 4000
MAX_RESULTS = 25
NO_TEXT = "(no readable text)"


class TextExtractor(HTMLParser):
    SKIP = {"script", "style", "head"}

    def __init__(self):
        super().__init__()
        self.parts = []
        self.skipping = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skipping += 1
        elif tag in {"br", "p", "div", "li", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skipping:
            self.skipping -= 1

    def handle_data(self, data):
        if not self.skipping:
            self.parts.append(data)


def html_to_text(html):
    parser = TextExtractor()
    parser.feed(html)
    lines = (line.strip() for line in "".join(parser.parts).splitlines())

    return "\n".join(line for line in lines if line)


def decode(part):
    data = part.get("body", {}).get("data")

    if not data:
        return ""

    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode(
        "utf-8", errors="replace"
    )


def find_part(payload, mime_type):
    """Depth-first search for the first non-empty part of a MIME type."""
    if payload.get("mimeType") == mime_type and not payload.get("filename"):
        text = decode(payload)

        if text.strip():
            return text

    for part in payload.get("parts", []):
        found = find_part(part, mime_type)

        if found:
            return found

    return ""


def extract_text(payload):
    plain = find_part(payload, "text/plain")

    if plain:
        return plain.strip()

    html = find_part(payload, "text/html")

    return html_to_text(html) if html else ""


def header(message, name):
    for item in message.get("payload", {}).get("headers", []):
        if item["name"].lower() == name.lower():
            return item["value"]

    return ""


def summary(message):
    return {
        "id": message["id"],
        "from": header(message, "From"),
        "subject": header(message, "Subject"),
        "date": header(message, "Date"),
    }


def get_service(service):
    return service or build(
        "gmail", "v1", credentials=get_credentials(), cache_discovery=False
    )


def search_emails(query, limit=10, *, service=None):
    """Search with Gmail syntax. Returns metadata and a snippet only."""
    service = get_service(service)
    limit = max(1, min(int(limit), MAX_RESULTS))
    messages = service.users().messages()

    found = messages.list(userId="me", q=query, maxResults=limit).execute()

    results = []

    for item in found.get("messages", []):
        message = messages.get(
            userId="me",
            id=item["id"],
            format="metadata",
            metadataHeaders=["From", "Subject", "Date"],
        ).execute()

        results.append({**summary(message), "snippet": message.get("snippet", "")})

    return results


def read_email(id, *, service=None):
    """Read one email as plain text, truncated to MAX_BODY_CHARS."""
    if not id:
        raise ValueError("An email id is required.")

    service = get_service(service)
    message = service.users().messages().get(
        userId="me", id=id, format="full"
    ).execute()

    body = extract_text(message.get("payload", {})) or NO_TEXT
    truncated = len(body) > MAX_BODY_CHARS

    if truncated:
        body = body[:MAX_BODY_CHARS] + "\n[truncated]"

    return {**summary(message), "body": body, "truncated": truncated}
