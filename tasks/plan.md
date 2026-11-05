# Implementation Plan: MVP

Replanned 2026-11-05 after Task 2. The original agent-core plan is cut down to
what a first working app needs. Tasks are tracked in [todo.md](todo.md).

## MVP definition (confirmed 2026-11-05)

A **menu-bar app** that opens a chat window. You ask in plain language and a
**local Ollama model** answers from your **Apple Notes, Google Calendar, and
Gmail**. It's **read-only**: it never creates, edits, sends, or deletes anything.

## Done so far

- [x] Task 1: Fix test collection (`890dfcd`)
- [x] Task 2: `Session.send` with Ollama and memory (`de02041`, `8c0c179`, `e36dc90`)
- [x] Bug fix: `schemas.py` syntax error (`f79d2c4`)

## Architecture Decisions

- **Read-only means no approval system.** Every MVP tool is a read, so
  `action-guard`, pause/resume, and confirm cards are deferred. The
  `dispatch()` seam stays so they can be added later without rework.
- **Google OAuth with read-only scopes** (`calendar.readonly`,
  `gmail.readonly`). A bug or prompt injection can't change your data.
- **Token stored in a local file** (`~/.config/personal-agent/token.json`,
  mode 600). Keychain comes later.
- **Personal data stays local.** Calendar and Gmail tools get the same
  local-Ollama-only check as Notes. With Claude escalation deferred, no
  personal data leaves the laptop.
- **Fake in-memory tasks and calendar are removed.** A real app must not answer
  from made-up data. `get_calendar_events` is replaced by Google Calendar, and
  `get_tasks` and `create_task` are dropped until a real task source exists.
- **UI stack:** FastAPI serves one chat page from `frontend/`. A `rumps`
  menu-bar icon opens it in a `pywebview` window. Everything runs in one
  Python process.

## New dependencies (approving this plan approves these)

`google-api-python-client`, `google-auth-oauthlib` (Google APIs) ·
`uvicorn`, `httpx` (serve FastAPI; `httpx` for FastAPI's test client) ·
`rumps`, `pywebview` (menu bar and window)

## Task List

### Phase 1: Usable in the terminal
- [ ] Task 3: Friendly errors (Ollama down, step limit)
- [ ] Task 4: CLI on `Session`; delete router

### Checkpoint 1: chat over Notes works in the CLI

### Phase 2: Google data
- [ ] Task 5: Google sign-in (read-only)
- [ ] Task 6: Google Calendar read; remove fake data
- [ ] Task 7: Gmail search and read

### Checkpoint 2: morning check works in the CLI

### Phase 3: The app
- [ ] Task 8: Chat API and chat page
- [ ] Task 9: Menu-bar app

### Checkpoint 3: MVP done

## Deferred (after MVP)

Writes (create note, add event, drafts), then `action-guard` and pause/resume
for send, edit, and delete · "Ask Claude instead" · tool-use eval script ·
history trimming and truncation · Keychain token storage · streaming replies ·
Reminders, Docs, Drive, Notion, habits.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| 7B model picks the wrong tool or gives a bad answer | High | Few, clearly described tools; errors go back to the model; you judge quality at Checkpoint 1 and we switch models if needed |
| Google OAuth setup is fiddly (Cloud project, consent screen, test user) | Med | Task 5 includes a step-by-step setup section in the README; you do the one-time console steps |
| Email bodies are long and full of HTML, overflowing a 7B context | Med | `read_email` returns plain text, truncated to 4,000 characters, same as notes |
| `pywebview` or `rumps` problems on Python 3.14 | Med | Task 9 starts with a spike; fallback is opening the chat page in the default browser from the menu-bar icon |
| Prompt injection inside an email or note | Low (read-only) | Already in the system prompt: content is data, not instructions. Read-only scopes cap the damage |
