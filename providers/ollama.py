import json
import os

import requests

from providers import Reply, ToolCall


DEFAULT_HOST = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:7b"


def convert_tools(tools):
    """Convert Claude-style tool schemas to Ollama format."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            },
        }
        for tool in tools
    ]


def to_ollama_messages(history, system):
    """Convert neutral history to Ollama chat messages."""
    messages = [{"role": "system", "content": system}]

    for message in history:
        role = message["role"]

        if role == "tool":
            messages.append({
                "role": "tool",
                "tool_name": message["name"],
                "content": json.dumps(message["result"]),
            })
            continue

        if role == "assistant":
            converted = {"role": "assistant", "content": message["text"]}

            if message.get("tool_calls"):
                converted["tool_calls"] = [
                    {
                        "function": {
                            "name": call["name"],
                            "arguments": call["arguments"],
                        },
                    }
                    for call in message["tool_calls"]
                ]

            messages.append(converted)
            continue

        messages.append({"role": "user", "content": message["text"]})

    return messages


def parse_reply(message):
    """Convert an Ollama assistant message to a Reply."""
    tool_calls = []

    for call in message.get("tool_calls") or []:
        function = call["function"]
        arguments = function.get("arguments") or {}

        if isinstance(arguments, str):
            arguments = json.loads(arguments)

        tool_calls.append(
            ToolCall(name=function["name"], arguments=arguments)
        )

    return Reply(
        text=message.get("content") or "",
        tool_calls=tool_calls,
    )


class OllamaAdapter:
    name = "ollama"

    def chat(self, history, *, system, tools):
        """Send the conversation to Ollama and return its reply."""
        host = os.getenv("OLLAMA_HOST", DEFAULT_HOST)

        response = requests.post(
            f"{host}/api/chat",
            json={
                "model": os.getenv("OLLAMA_MODEL", DEFAULT_MODEL),
                "stream": False,
                "messages": to_ollama_messages(history, system),
                "tools": convert_tools(tools),
            },
            timeout=120,
            allow_redirects=False,
        )

        response.raise_for_status()
        return parse_reply(response.json()["message"])
