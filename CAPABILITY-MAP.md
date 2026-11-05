# Capability Map: Personal Agent v1

Approved: 2026-11-05

**Intent:** A macOS menu-bar chat app. You ask in plain language and it reads,
summarizes, and acts on your Google Calendar, Gmail, and Apple Notes. Runs on a
local Ollama model by default. Claude is used only when you click
"Ask Claude instead". Single user, M1 with 16 GB of RAM.

| Module id | Responsibility | Depends on | Spec |
|---|---|---|---|
| `agent-core` | Ollama-first chat loop, tool calling, conversation state, on-demand Claude call | — | [SPEC-agent-core.md](SPEC-agent-core.md) |
| `action-guard` | Sort each tool call into auto, confirm, or warn; hold pending actions; build previews; detect new contacts | `agent-core` | — |
| `apple-notes` | List, search, read, create, and edit notes through AppleScript | `action-guard` | — |
| `google-auth` | OAuth flow, token storage in Keychain, token refresh | — | — |
| `google-calendar` | Read events; create, edit, move, and delete events; invites | `google-auth`, `action-guard` | — |
| `gmail` | Search, read, and summarize threads; drafts; send; reply | `google-auth`, `action-guard` | — |
| `chat-api` | FastAPI endpoints: message, stream, approve or reject, escalate | `agent-core`, `action-guard` | — |
| `menubar-ui` | Menu-bar icon, chat window, confirm cards, "Ask Claude instead" button | `chat-api` | — |

**Build order:**

1. `agent-core` → `action-guard` → `apple-notes` (first usable version: chat over Notes in the CLI)
2. `chat-api` → `menubar-ui` (the real app, working with Notes)
3. `google-auth` → `google-calendar` → `gmail`

## Safety tiers (owned by `action-guard`, used by every integration)

| Tier | Actions |
|---|---|
| **auto** | All reads and summaries, create a note, add an event for yourself only, save an email draft |
| **confirm** (preview, then OK) | Send email, edit or move an existing event, edit an existing note |
| **warn** (confirm with extra warning) | Delete anything, email someone not emailed before, invite other people |

## Later (not v1)

Reminders and tasks, Google Docs, Google Drive, Notion, habit tracking (local data, streaks).

## Out of scope

WhatsApp, mobile or web versions, multiple users, paid APIs by default,
automatic escalation to Claude.
