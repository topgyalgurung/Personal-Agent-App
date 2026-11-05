# Tasks: MVP

Plan: [plan.md](plan.md) · Module spec: [SPEC-agent-core.md](../SPEC-agent-core.md)

Done: Task 1 (test collection), Task 2 (`Session.send`), schema fix. See plan.md.

---

## Task 3: Friendly errors (Ollama down, step limit)

**Description:** If Ollama refuses the connection or times out (60 s), or the
model goes past 8 tool steps, `send` returns a `Turn` with `error` set instead
of raising. Malformed tool-argument JSON from Ollama becomes an error result
the model sees, not a crash.

**Acceptance criteria:**
- [x] Ollama connection refused or timeout returns `Turn(error="Ollama isn't running. Start it with: ollama serve")`
- [x] More than 8 tool steps returns a `Turn` with an error and the tool calls made so far
- [x] Malformed argument JSON gives the model an error result and the loop continues

**Verification:**
- [x] `uv run pytest -q`

**Dependencies:** None
**Files:** `agent_core.py`, `providers/ollama.py`, `tests/test_agent_core.py`, `tests/test_providers.py`
**Scope:** S

---

## Task 4: CLI on `Session`; delete router

**Description:** `main.py` keeps one `Session` and prints `Turn.text` or
`Turn.error`. Delete `router.py` and `ollama_agent.py`, and drop
`LLM_PROVIDER`. `agent.py` stays for the later Claude adapter but isn't used.
`prompts.py` uses the system timezone. Update the README.

**Acceptance criteria:**
- [ ] `router.py`, `ollama_agent.py`, and `LLM_PROVIDER` are gone; `main.py` uses `Session`
- [ ] System prompt shows the local timezone
- [ ] README describes the local-only MVP

**Verification:**
- [ ] `uv run pytest -q`
- [ ] Manual: `uv run python main.py`, with Notes enabled, a two-turn
      conversation where turn 2 uses turn 1's context
- [ ] Manual: with Ollama stopped, the CLI shows the start message

**Dependencies:** Task 3
**Files:** `main.py`, `router.py`, `ollama_agent.py`, `prompts.py`, `README.md`
**Scope:** M

---

## Checkpoint 1: chat over Notes works in the CLI
- [ ] `uv run pytest -q` passes
- [ ] You try `qwen2.5:7b` on real questions about your notes; keep or switch models

---

## Task 5: Google sign-in (read-only)

**Description:** `integrations/google_auth.py` runs the installed-app OAuth
flow with scopes `calendar.readonly` and `gmail.readonly`. It uses the
`credentials.json` you download from your Google Cloud project, saves the token
to `~/.config/personal-agent/token.json` with mode 600, and refreshes it when it
expires. `uv run python -m integrations.google_auth` signs you in. The README
gets one-time Google Cloud setup steps.

**Acceptance criteria:**
- [ ] Valid saved token is loaded without a browser; expired token is refreshed and re-saved
- [ ] Token file is created with mode 600; only read-only scopes are requested
- [ ] Missing `credentials.json` or not signed in gives a clear "run sign-in" error

**Verification:**
- [ ] `uv run pytest tests/test_google_auth.py -q` (fakes, no network)
- [ ] Manual: sign in once, then rerun with no browser prompt

**Dependencies:** None (can run in parallel with Tasks 3–4)
**Files:** `integrations/google_auth.py`, `tests/test_google_auth.py`, `pyproject.toml`, `README.md`, `.gitignore`
**Scope:** M

---

## Task 6: Google Calendar read; remove fake data

**Description:** `integrations/google_calendar.py` adds a `list_events` tool
(start and end dates, defaulting to today). It returns title, start, end,
location, and attendee count, ordered by start time. Replace the fake
`get_calendar_events`, and remove fake `get_tasks` and `create_task` from
`tools.py`, `schemas.py`, and the registry. Calendar access gets the same
local-only check as Notes.

**Acceptance criteria:**
- [ ] `list_events` returns events in range, ordered, with all-day events handled
- [ ] Fake tasks and calendar tools are gone from schemas and the registry
- [ ] Calendar tools are blocked for non-local providers

**Verification:**
- [ ] `uv run pytest -q` (fake Calendar service, no network)
- [ ] Manual: CLI "what's on my calendar today?" matches Google Calendar

**Dependencies:** Tasks 4, 5
**Files:** `integrations/google_calendar.py`, `tools.py`, `schemas.py`, `tool_dispatch.py`, `tests/test_google_calendar.py`
**Scope:** M

---

## Task 7: Gmail search and read

**Description:** `integrations/gmail.py` adds `search_emails(query, limit)`,
which uses Gmail search syntax and returns sender, subject, date, snippet, and
id. It also adds `read_email(id)`, which returns a plain-text body (HTML
stripped) truncated to 4,000 characters. The prompt marks email content as
untrusted. Same local-only check.

**Acceptance criteria:**
- [ ] Search returns metadata only; read returns plain text with a truncation marker
- [ ] HTML-only and multipart emails produce readable text
- [ ] Gmail tools are blocked for non-local providers

**Verification:**
- [ ] `uv run pytest -q` (fake Gmail service, no network)
- [ ] Manual: CLI "any unread emails from today?" matches Gmail

**Dependencies:** Tasks 5, 6
**Files:** `integrations/gmail.py`, `schemas.py`, `tool_dispatch.py`, `prompts.py`, `tests/test_gmail.py`
**Scope:** M

---

## Checkpoint 2: morning check works in the CLI
- [ ] "What's my day look like?" uses Calendar, Gmail, and Notes correctly
- [ ] Review with you before building the UI

---

## Task 8: Chat API and chat page

**Description:** `server.py` is a FastAPI app with one `Session`. `POST /api/chat`
takes `{"message"}` and returns `{"text", "error", "tools"}`. `GET /` serves
`frontend/index.html`, a single-page chat with a message list, an input box, and
a loading state. It binds to `127.0.0.1` only.

**Acceptance criteria:**
- [ ] `POST /api/chat` returns the turn; consecutive calls share memory
- [ ] Empty message gets a 422; agent errors come back in `error`, not as a 500
- [ ] Chat page sends a message and shows the reply

**Verification:**
- [ ] `uv run pytest tests/test_server.py -q` (TestClient, fake adapter)
- [ ] Manual: `uv run uvicorn server:app`, then chat at http://127.0.0.1:8000

**Dependencies:** Task 4
**Files:** `server.py`, `frontend/index.html`, `tests/test_server.py`, `pyproject.toml`
**Scope:** M

---

## Task 9: Menu-bar app

**Description:** `app.py` starts uvicorn in a background thread and shows a
`rumps` menu-bar icon with "Open chat" and "Quit". "Open chat" shows a
`pywebview` window on the chat page. Start with a spike to confirm
`rumps` and `pywebview` work together on Python 3.14. If they don't, fall back
to opening the page in the default browser.

**Acceptance criteria:**
- [ ] `uv run python app.py` shows the menu-bar icon; no Dock icon
- [ ] "Open chat" opens the chat window; "Quit" stops the server and exits

**Verification:**
- [ ] Manual: launch, chat, close the window, reopen (conversation kept), quit

**Dependencies:** Task 8
**Files:** `app.py`, `pyproject.toml`, `README.md`
**Scope:** S

---

## Checkpoint 3: MVP done
- [ ] Use it for a morning: Calendar, Gmail, and Notes questions answered from the menu bar
- [ ] `uv run pytest -q` passes; README covers setup and launch
- [ ] Decide what comes next from the Deferred list
