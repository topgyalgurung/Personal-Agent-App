"""
Model adapters.

Every adapter has a `name` and one method:

    chat(history, *, system, tools) -> Reply

`history` is the provider-neutral list kept by agent_core. Each adapter
converts it to its own API format and converts the answer back to a Reply.
"""
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    name: str
    arguments: dict
    id: str | None = None


@dataclass
class Reply:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
