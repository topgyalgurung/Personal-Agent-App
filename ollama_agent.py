
import os
import json
import requests

from dotenv import load_dotenv
from agent import execute_tool
from schemas import TOOLS
from prompts import get_system_prompt

load_dotenv()

OLLAMA = os.getenv(
    "OLLAMA_HOST",
    "http://localhost:11434"
)
CHAT_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")


def convert_tools():
    """Convert Claude tool schemas to Ollama format."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            },
        }
        for tool in TOOLS
    ]


def ask_llm(messages):
    """Send messages to Ollama REST API."""
    response = requests.post(
        f"{OLLAMA}/api/chat",
        json={
            "model": CHAT_MODEL,
            "stream": False,
            "messages": messages,
            "tools": convert_tools(),
        },
        timeout=120,
    )

    response.raise_for_status()
    return response.json()["message"]


def run_ollama_agent(prompt):
    """Run Ollama agent with tool calling."""
    messages = [
        {
            "role": "system",
            "content": get_system_prompt(),
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]

    for _ in range(10):
        message = ask_llm(messages)

        # Preserve assistant response.
        messages.append(message)

        tool_calls = message.get("tool_calls", [])

        # No tools requested: return final answer.
        if not tool_calls:
            return message.get("content", "")

        for call in tool_calls:
            function = call["function"]
            name = function["name"]
            arguments = function.get("arguments", {})

            if isinstance(arguments, str):
                arguments = json.loads(arguments)

            print(f"[Ollama tool: {name}]")

            try:
                result = execute_tool(
                    name,
                    arguments,
                )
            except Exception as error:
                result = {
                    "success": False,
                    "error": str(error),
                }

            # Return tool result to Ollama.
            messages.append({
                "role": "tool",
                "tool_name": name,
                "content": json.dumps(result),
            })

    raise RuntimeError(
        "Ollama exceeded maximum tool iterations"
    )
