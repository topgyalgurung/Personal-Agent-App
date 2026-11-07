# integrations/apple_notes.py

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).with_suffix(".applescript")


class NotesError(RuntimeError):
    pass


def _fetch(operation, value="", limit=20, max_chars=4000):
    if sys.platform != "darwin":
        raise NotesError("Apple Notes requires macOS.")

    if operation not in {"list", "search", "read"}:
        raise ValueError("Unsupported Notes operation.")

    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError("Invalid query or note ID.")

    if operation != "list" and not value.strip():
        raise ValueError("A query or note ID is required.")

    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50.")

    if type(max_chars) is not int or not 1 <= max_chars <= 12000:
        raise ValueError("max_chars must be between 1 and 12000.")

    try:
        result = subprocess.run(
            [
                "/usr/bin/osascript",
                str(SCRIPT),
                operation,
                value,
                str(limit),
                str(max_chars),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        raise NotesError("Notes timed out.") from None
    except subprocess.CalledProcessError as error:
        if "-1743" in (error.stderr or ""):
            message = "Allow your terminal or editor to access Notes."
        else:
            message = "Notes unavailable or the requested note is locked."

        # Avoid exposing raw errors that could contain private data.
        raise NotesError(message) from None
    except OSError:
        raise NotesError("Could not start the Notes reader.") from None

    try:
        rows = json.loads(result.stdout)

        if not isinstance(rows, list):
            raise ValueError()

        for row in rows:
            if not isinstance(row, dict):
                raise ValueError()

            if not all(
                isinstance(row.get(key), str)
                for key in ("id", "title", "folder")
            ):
                raise ValueError()

    except (ValueError, TypeError):
        raise NotesError("Invalid response from Notes.") from None

    return {
        "success": True,
        "source": "apple_notes",
        "untrusted_content": True,
        "notes": rows,
    }


def list_notes(limit=20):
    return _fetch("list", limit=limit)


def search_notes(query, limit=20):
    return _fetch("search", value=query, limit=limit)


def read_note(note_id, max_chars=4000):
    result = _fetch(
        "read",
        value=note_id,
        limit=1,
        max_chars=max_chars,
    )

    if not result["notes"]:
        return {
            "success": False,
            "error": "Note not found.",
        }

    return result