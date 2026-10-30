# Personal Action AI Agent

A Python-based AI assistant for managing tasks, calendar events, and daily priorities, featuring **Claude API with automatic Ollama fallback**.

## Architecture

```text
User → Router → Claude API (Primary)
                 ↓ On API failure
               Ollama (Local)
                 ↓
            Shared Python Tools
                 ↓
             AI Response
```

## LLM Fallback

The application uses a custom `router.py` to manage model selection and fallback.

- **Claude:** Primary LLM using Anthropic's Messages API.
- **Ollama:** Local fallback using the `/api/chat` REST endpoint.
- **Automatic fallback:** Handles authentication, rate-limit, connection, and server errors.
- **Shared tools:** Both providers support task management and calendar operations.
- **Clean output:** Internal API errors are logged rather than displayed to users.

## Project Structure

```text
├── main.py           # CLI entry point
├── router.py         # Provider routing and fallback
├── agent.py          # Claude agent and tool loop
├── ollama_agent.py   # Ollama REST API agent
├── tools.py          # Task and calendar functions
├── schemas.py        # Tool definitions
└── prompts.py        # System instructions
```

## Setup

Install dependencies:

```bash
uv sync
```

Configure `.env`:

```env
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=your_api_key
CLAUDE_MODEL=claude-haiku-4-5
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen3:4b
```

Install the local model:

```bash
ollama pull qwen3:4b
```

Run the agent:

```bash
uv run main.py
```

Set `LLM_PROVIDER=ollama` to run locally without Claude.

## Tech Stack

Python · uv · Anthropic SDK · Ollama · Requests · Pytest

## Limitations & Next Steps

Fallback restarts the request, so write operations need idempotency protection to prevent duplicates. Planned improvements include persistent memory, API cost tracking, automated evaluations, and intelligent model routing.