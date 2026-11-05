"""
Chat engine: local Ollama by default, Claude only when the user asks.

History is a provider-neutral list of dicts, converted by each adapter:

    {"role": "user", "text": str}
    {"role": "assistant", "text": str, "tool_calls": [{"id", "name", "arguments"}]}
    {"role": "tool", "call_id": str, "name": str, "result": object}
"""
import logging
import uuid
from dataclasses import dataclass, field

from prompts import get_system_prompt
from providers import ProviderUnavailable
from providers.ollama import OllamaAdapter
from schemas import TOOLS
from tool_dispatch import dispatch


logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 8


@dataclass
class ToolRecord:
    id: str
    name: str
    arguments: dict
    result: object


@dataclass
class Turn:
    id: str
    provider: str
    text: str
    tool_calls: list[ToolRecord] = field(default_factory=list)
    pending: dict | None = None
    error: str | None = None


class Session:
    def __init__(
        self,
        adapter=None,
        *,
        system_prompt=get_system_prompt,
        tools=TOOLS,
    ):
        self.adapter = adapter or OllamaAdapter()
        self.system_prompt = system_prompt
        self.tools = tools
        self.history = []
        self._call_count = 0

    def send(self, user_text):
        """Answer a new user message with the default adapter."""
        checkpoint = len(self.history)
        self.history.append({"role": "user", "text": user_text})

        turn = self._run_tool_loop(self.adapter)

        # A failed turn is dropped so a retry starts clean.
        if turn.error:
            del self.history[checkpoint:]

        return turn

    def _run_tool_loop(self, adapter):
        """Call the model until it answers without requesting tools."""
        records = []

        for _ in range(MAX_TOOL_ITERATIONS):
            try:
                reply = adapter.chat(
                    self.history,
                    system=self.system_prompt(),
                    tools=self.tools,
                )
            except ProviderUnavailable as error:
                return self._failed(adapter, str(error), records)

            calls = [self._with_id(call) for call in reply.tool_calls]

            self.history.append({
                "role": "assistant",
                "text": reply.text,
                "tool_calls": [
                    {"id": c.id, "name": c.name, "arguments": c.arguments}
                    for c in calls
                ],
            })

            if not calls:
                return Turn(
                    id=uuid.uuid4().hex,
                    provider=adapter.name,
                    text=reply.text,
                    tool_calls=records,
                )

            for call in calls:
                result = self._run_tool(call, provider=adapter.name)

                self.history.append({
                    "role": "tool",
                    "call_id": call.id,
                    "name": call.name,
                    "result": result,
                })
                records.append(
                    ToolRecord(call.id, call.name, call.arguments, result)
                )

        return self._failed(
            adapter,
            f"I stopped after {MAX_TOOL_ITERATIONS} tool steps without an "
            "answer. Try asking a simpler or more specific question.",
            records,
        )

    def _failed(self, adapter, error, records):
        return Turn(
            id=uuid.uuid4().hex,
            provider=adapter.name,
            text="",
            tool_calls=records,
            error=error,
        )

    def _with_id(self, call):
        """Give calls without a provider id a session-unique one."""
        if call.id is None:
            self._call_count += 1
            call.id = f"call_{self._call_count}"

        return call

    def _run_tool(self, call, *, provider):
        """Run one tool call; failures become error results for the model."""
        logger.debug("Tool call: %s", call.name)

        if call.error:
            return {"success": False, "error": call.error}

        try:
            outcome = dispatch(call.name, call.arguments, provider=provider)
        except Exception as error:
            logger.warning(
                "Tool %s failed: %s", call.name, type(error).__name__
            )
            return {"success": False, "error": str(error)}

        return outcome.result
