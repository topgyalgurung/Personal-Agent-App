import os
from dataclasses import dataclass
from urllib.parse import urlparse

import tools


NOTES_TOOLS = {
    "list_notes",
    "search_notes",
    "read_note",
}

GOOGLE_TOOLS = {
    "list_events",
}

REGISTRY = {
    name: getattr(tools, name)
    for name in [
        *NOTES_TOOLS,
        *GOOGLE_TOOLS,
    ]
}


def check_local_ollama():
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


def check_google_access(provider):
    """Calendar and Gmail data never leaves this laptop."""
    if provider != "ollama":
        raise PermissionError(
            "Google data stays on this laptop. Use local Ollama."
        )

    try:
        check_local_ollama()
    except PermissionError:
        raise PermissionError(
            "Google data requires a local Ollama endpoint and model."
        )


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
        check_local_ollama()

    else:
        raise PermissionError("Unknown provider.")


def execute_tool(name, arguments, *, provider="claude"):
    if name not in REGISTRY:
        raise ValueError("Unknown tool.")

    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be an object.")

    if name in NOTES_TOOLS:
        check_notes_access(provider)

    if name in GOOGLE_TOOLS:
        check_google_access(provider)

    return REGISTRY[name](**arguments)


@dataclass
class Executed:
    result: object


@dataclass
class NeedsApproval:
    action: dict


def needs_approval(name, arguments):
    """Pass-through guard. action-guard replaces this with real rules."""
    return False


def dispatch(name, arguments, *, provider, cloud_consent=False):
    """Run a tool call, or hold it for approval."""
    if needs_approval(name, arguments):
        return NeedsApproval({"name": name, "arguments": arguments})

    return Executed(execute_tool(name, arguments, provider=provider))
