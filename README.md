# Personal Action AI Agent

A local, read-only assistant for your personal data. Ask in plain language and a
local Ollama model answers from your Google Calendar, Gmail, and Apple Notes.
It lives in the macOS menu bar. Nothing leaves your laptop, and it can't create,
edit, send, or delete anything.

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
└── agent.py          # Claude agent, unused until "Ask Claude instead"
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

Python · uv · Ollama · FastAPI · rumps · pywebview · Google APIs · Pytest
