import os
from urllib.parse import urlparse

import tools


NOTES_TOOLS = {
    "list_notes",
    "search_notes",
    "read_note",
}

REGISTRY = {
    name: getattr(tools, name)
    for name in [
        "get_tasks",
        "get_calendar_events",
        "create_task",
        *NOTES_TOOLS,
    ]
}


def check_notes_access(provider):
    if os.getenv("APPLE_NOTES_ENABLED", "0") != "1":
        raise PermissionError("Apple Notes access is disabled.")

    if provider == "claude":
        if os.getenv("APPLE_NOTES_ALLOW_CLOUD", "0") != "1":
            raise PermissionError(
                "Notes sharing with Claude is blocked. "
                "Switch to Ollama for local analysis."
            )

    elif provider == "ollama":
        host = urlparse(
            os.getenv("OLLAMA_HOST", "http://localhost:11434")
        )

        if (
            host.scheme != "http"
            or host.hostname not in {"localhost", "127.0.0.1", "::1"}
        ):
            raise PermissionError(
                "Notes require a local Ollama endpoint."
            )

        if ":cloud" in os.getenv("OLLAMA_MODEL", "").lower():
            raise PermissionError("Choose a downloaded local model.")

    else:
        raise PermissionError("Unknown provider.")


def execute_tool(name, arguments, *, provider="claude"):
    if name not in REGISTRY:
        raise ValueError("Unknown tool.")

    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be an object.")

    if name in NOTES_TOOLS:
        check_notes_access(provider)

    return REGISTRY[name](**arguments)