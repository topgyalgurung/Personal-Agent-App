# Personal Action AI Agent

A local, read-only assistant for your personal data. Ask in plain language and a
local Ollama model answers from your Apple Notes. Google Calendar and Gmail come
next, then a menu-bar chat window. Nothing leaves your laptop.

## How it works

```
main.py (CLI)
  → agent_core.Session keeps the conversation
    → providers/ollama.py asks the local model
      → model requests a tool
        → tool_dispatch.py checks privacy settings
          → Python runs a fixed AppleScript
            → Notes returns structured data
          ← tool result goes back to the model
      ← model answers
```

Status: the MVP plan is in `tasks/plan.md`. Today the CLI reads Apple Notes only.
Calendar, Gmail, and the menu-bar app are planned. Claude is not used.

## Project Structure

```text
├── main.py           # CLI entry point
├── agent_core.py     # Session: conversation memory and tool loop
├── providers/        # Model adapters (Ollama)
├── tool_dispatch.py  # Runs tools, privacy check
├── integrations/     # Apple Notes (AppleScript)
├── schemas.py        # Tool definitions
├── prompts.py        # System instructions
├── agent.py          # Claude agent, unused until "Ask Claude instead"
└── tools.py          # Placeholder tasks and calendar, to be replaced
```

## Setup

Install dependencies:

```bash
uv sync
```

Install the local model:

```bash
ollama pull qwen2.5:7b
```

Optional `.env`:

```env
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
```

Run the agent (Ollama must be running: `ollama serve`):

```bash
uv run python main.py
```

Run the tests:

```bash
uv run pytest -q
```

## Tech Stack

Python · uv · Ollama · Requests · Pytest
