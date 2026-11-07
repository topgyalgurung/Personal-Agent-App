
import json
import os

from anthropic import Anthropic
from dotenv import load_dotenv

from prompts import get_system_prompt
from schemas import TOOLS

# from tools import (
#     get_tasks,
#     get_calendar_events,
#     create_task,
# )
from tool_dispatch import execute_tool

load_dotenv()

MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5")

# def execute_tool(name: str, arguments: dict):
#     """Execute a tool requested by Claude."""

#     if name == "get_tasks":
#         return get_tasks()

#     if name == "get_calendar_events":
#         return get_calendar_events()

#     if name == "create_task":
#         return create_task(**arguments)

#     raise ValueError(f"Unknown tool: {name}")


def run_agent(user_message: str) -> str:
    """Run Claude until it completes the request."""
    client = Anthropic()

    messages = [
        {
            "role": "user",
            "content": user_message,
        }
    ]

    for iteration in range(10):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=get_system_prompt(),
            tools=TOOLS,
            messages=messages,
        )

        print(
            f"\n[Claude stop_reason: "
            f"{response.stop_reason}]"
        )

        if response.stop_reason == "end_turn":
            return "\n".join(
                block.text
                for block in response.content
                if block.type == "text"
            )

        if response.stop_reason != "tool_use":
            raise RuntimeError(
                f"Unexpected stop reason: "
                f"{response.stop_reason}"
            )

        # Preserve Claude's entire response.
        messages.append({
            "role": "assistant",
            "content": response.content,
        })

        tool_results = []

        for block in response.content:
            if block.type != "tool_use":
                continue

            print(
                f"[Tool call: {block.name} "
                f"{block.input}]"
            )

            try:
                result = execute_tool(
                    block.name,
                    block.input,
                )
                is_error = False

                if (
                    isinstance(result, dict)
                    and result.get("success") is False
                ):
                    is_error = True

            except Exception as error:
                result = {
                    "success": False,
                    "error": str(error),
                }
                is_error = True

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result),
                "is_error": is_error,
            })

        # Return all tool results together.
        messages.append({
            "role": "user",
            "content": tool_results,
        })

    raise RuntimeError(
        "Agent exceeded maximum tool iterations"
    )
