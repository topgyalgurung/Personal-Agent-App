import json
import os

import requests

from providers import ProviderUnavailable, Reply, ToolCall


DEFAULT_HOST = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:7b"
TIMEOUT_SECONDS = 60


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


def parse_arguments(arguments):
    """Return (arguments, error). Small models often send bad JSON."""
    if not arguments:
        return {}, None

    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            return {}, "Tool arguments were not valid JSON."

    if not isinstance(arguments, dict):
        return {}, "Tool arguments must be a JSON object."

    return arguments, None


def parse_reply(message):
    """Convert an Ollama assistant message to a Reply."""
    tool_calls = []

    for call in message.get("tool_calls") or []:
        function = call["function"]
        arguments, error = parse_arguments(function.get("arguments"))

        tool_calls.append(
            ToolCall(name=function["name"], arguments=arguments, error=error)
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
        model = os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)

        try:
            response = requests.post(
                f"{host}/api/chat",
                json={
                    "model": model,
                    "stream": False,
                    "messages": to_ollama_messages(history, system),
                    "tools": convert_tools(tools),
                },
                timeout=TIMEOUT_SECONDS,
                allow_redirects=False,
            )
        except requests.ConnectionError:
            raise ProviderUnavailable(
                "Ollama isn't running. Start it with: ollama serve"
            )
        except requests.Timeout:
            raise ProviderUnavailable(
                f"Ollama didn't answer within {TIMEOUT_SECONDS} seconds. "
                "It may still be loading the model; try again."
            )

        if response.status_code == 404:
            raise ProviderUnavailable(
                f"Model {model} isn't downloaded. Run: ollama pull {model}"
            )

        if not response.ok:
            raise ProviderUnavailable(
                f"Ollama returned an error (status {response.status_code})."
            )

        return parse_reply(response.json()["message"])
