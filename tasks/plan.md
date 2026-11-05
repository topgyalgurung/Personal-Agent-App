# Implementation Plan: agent-core

Implements [SPEC-agent-core.md](../SPEC-agent-core.md) (approved 2026-11-05).
Tasks are tracked in [todo.md](todo.md).

## Overview

Replace the "Claude first, Ollama on failure" router with a `Session`. A session
answers with local Ollama, remembers the conversation, re-answers a turn with
Claude only on request, and can pause a turn for approval. The CLI moves onto
`Session`. `chat-api` and `menubar-ui` will use the same interface later.

## Current state (checked 2026-11-05)

- `uv run pytest` fails at collection (`No module named 'tools'`) because the
  project root isn't on `sys.path`. `uv run python -m pytest` passes 7/7. Task 1
  fixes this.
- Much of the work is uncommitted (agent.py, tools.py, schemas.py, tool_dispatch.py,
  integrations/, tests/test_notes.py). Commit it as a baseline before Task 1 so
  each task gets its own diff.
- Installed models: `qwen2:7b`, `llama3.2`. `qwen2.5:7b` and `llama3.1:8b`
  need to be pulled (Task 3).

## Architecture Decisions

- **Neutral history with synthetic call ids.** Ollama tool calls have no id.
  The history assigns each call an id (`call_<n>`) so it can be turned into
  Claude `tool_use`/`tool_result` pairs during escalation.
- **Thin adapters.** `providers/ollama.py` and `providers/claude.py` each expose
  `chat(messages, tools) -> Reply(text, tool_calls)`. All looping, history, and
  dispatch live in `agent_core.py`, so they're tested once with a fake adapter.
- **Pass-through guard first.** `dispatch()` returns `Executed | NeedsApproval`
  from the start. A pass-through version always executes. The pause and resume
  path is tested with a fake guard, and `action-guard` adds the real rules later.
- **Model quality is checked early.** The eval script runs right after the
  basic loop works (Task 3). If 7B tool use is poor, we find out before building
  more on top of it.

## Dependency graph

```
T1 test setup
 └─ T2 Session.send (Ollama, memory, pass-through dispatch)
     ├─ T3 eval script            ← risk check, run early
     ├─ T4 robustness
     │   └─ T5 CLI on Session, delete router
     │       └─ T7 escalate + consent ─┐
     ├─ T6 Claude adapter ─────────────┘
     └─ T8 pause/resume  (after T5, so the CLI can show y/n)
```

T3, T4, and T6 can be done in any order after T2.

## Task List

### Phase 1: Local chat
- [ ] Task 1: Fix test collection
- [ ] Task 2: `Session.send` with Ollama and multi-turn memory
- [ ] Task 3: Tool-use eval script and model comparison

### Checkpoint A0: model is good enough
- [ ] Eval results reviewed with user before continuing

- [ ] Task 4: Robustness for 7B models
- [ ] Task 5: CLI on `Session`; delete router

### Checkpoint A: local-only chat works
- [ ] Spec success criteria 2 and 4 pass by hand

### Phase 2: Claude on request
- [ ] Task 6: Claude adapter
- [ ] Task 7: `Session.escalate` with per-request cloud consent

### Phase 3: Approval seam
- [ ] Task 8: Pause and resume

### Checkpoint B: module complete
- [ ] All six spec success criteria met, README updated

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| 7B models pick the wrong tools or send bad arguments | High | Eval in Task 3 before building further; errors go back to the model for a retry (Task 4); Claude escalation as the manual fallback |
| Ollama's tool-call format differs between models or versions | Med | Adapter tests use fixture JSON from real `qwen2.5:7b` and `llama3.1:8b` replies captured in Task 3 |
| Claude rejects the synthesized tool_use/tool_result history | Med | Task 6 tests the conversion against the SDK's types; Task 7 runs one real escalation by hand |
| Personal data leaks to Claude outside escalation | High | `dispatch` rejects Claude calls without `cloud_consent`; explicit tests in Task 7 |
| A 10-turn history plus tool results overflows 8k context | Low | Trimming and 6,000-character truncation in Task 4; raise `num_ctx` if the eval shows truncation hurting answers |

## Open Questions

None blocking. The model choice is settled by the Task 3 eval results.
