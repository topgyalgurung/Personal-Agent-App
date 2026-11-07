# Personal Action AI Agent

A local, **read-only** assistant for your personal data. Ask in plain language
and a free, open-source Ollama model answers from your Google Calendar, Gmail,
and Apple Notes. It lives in the macOS menu bar. By default nothing leaves your
laptop.

## Status

| | |
|---|---|
| Reads Calendar, Gmail, Apple Notes | Working |
| Local model (Ollama) | Working |
| Editing, creating, sending, or deleting anything | **Not yet.** The agent is read-only today. Write actions are a stretch goal. |
| Model routing with Claude / OpenAI fallback | **Planned.** Not built yet. |

## Model strategy: cheap first, advanced only when needed

The app is built to spend as little as possible:

1. **Today:** every request goes to a free, open-source model running locally
   through Ollama (default `qwen2.5:7b`). No API costs.
2. **Planned:** an intelligent model router. It tries the free local model
   first. If a task needs a more capable or accurate model, the router falls
   back to the Claude API or the OpenAI API, or asks you before using one.
3. Paid models are the exception, not the default, so cost stays low.

Until the router lands, the app uses only the local model and tool calls are
blocked from reaching any non-local model (see `tool_dispatch.py`).

## How it works

```
menu-bar icon (app.py) → chat window → server.py (127.0.0.1 only)
  → agent_core.Session keeps the conversation
    → providers/ollama.py asks the local model
      → model requests a tool
        → tool_dispatch.py checks the model is local
          → Calendar / Gmail (read-only Google scopes) or Apple Notes
        ← tool result goes back to the model
    ← model answers
```

## Project Structure

```text
├── app.py            # Menu-bar app (rumps); opens the chat window
├── chat_window.py    # Native window (pywebview), run by app.py
├── server.py         # FastAPI: POST /api/chat, GET /
├── frontend/         # Chat page
├── main.py           # CLI alternative to the menu-bar app
├── agent_core.py     # Session: conversation memory and tool loop
├── providers/        # Model adapters (Ollama)
├── tool_dispatch.py  # Runs tools, local-only privacy check
├── tools.py          # Tools the model can call
├── integrations/     # Google auth, Calendar, Gmail, Apple Notes
├── schemas.py        # Tool definitions
├── prompts.py        # System instructions
└── agent.py          # Claude agent, unused until the model router is built
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

Enable Apple Notes access in `.env` (off by default):

```env
APPLE_NOTES_ENABLED=1
```

### Google sign-in (one time)

The app only asks for read-only access to Calendar and Gmail.

1. In the [Google Cloud console](https://console.cloud.google.com/), create a project.
2. Enable the **Google Calendar API** and the **Gmail API** (APIs & Services → Library).
3. Configure the OAuth consent screen: user type **External**, add your own
   Google account as a **test user**.
4. Create credentials: **OAuth client ID**, application type **Desktop app**.
   Download the JSON file.
5. Save it as `~/.config/personal-agent/credentials.json`.
6. Sign in once (a browser opens):

   ```bash
   uv run python -m integrations.google_auth
   ```

The token is saved to `~/.config/personal-agent/token.json` (owner-only
permissions) and refreshes itself. While the consent screen is in "Testing"
mode, Google expires the token after 7 days; just sign in again.

### Run

Ollama must be running (`ollama serve`).

```bash
uv run python app.py    # menu-bar app: click the icon → Open chat
uv run python main.py   # or chat in the terminal
```

If the chat window can't open, the menu-bar app opens the page in your browser.

Run the tests:

```bash
uv run pytest -q
```

## Tech Stack

Python · uv · Ollama (Claude/OpenAI fallback planned) · FastAPI · rumps · pywebview · Google APIs · Pytest

## Built with

Built with an AI coding assistant using the
[addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) pack. The
exact skills used are pinned in [agent-skills/skills-lock.json](agent-skills/skills-lock.json).
The work followed a spec-first, small-tasks workflow; see
[SPEC-agent-core.md](SPEC-agent-core.md) and [tasks/plan.md](tasks/plan.md).
