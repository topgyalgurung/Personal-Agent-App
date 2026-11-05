# Tasks: agent-core

Spec: [SPEC-agent-core.md](../SPEC-agent-core.md) · Plan: [plan.md](plan.md)

Baseline commit done on branch `agent-core` (2026-11-05).

---

## Task 1: Fix test collection

**Description:** `uv run pytest` can't import root modules. Add pytest config so
the root is on the path, and set the asyncio fixture loop scope to clear the
deprecation warning.

**Acceptance criteria:**
- [ ] `uv run pytest -q` collects and passes all 7 existing tests
- [ ] No `PytestDeprecationWarning` in the output

**Verification:**
- [ ] `uv run pytest -q`

**Dependencies:** None
**Files:** `pyproject.toml`
**Scope:** XS

---

## Task 2: `Session.send` with Ollama and multi-turn memory

**Description:** Add `agent_core.py` with `Session`, `Turn`, `ToolRecord`, the
neutral `History` (synthetic call ids), and the tool loop. Move the HTTP call
from `ollama_agent.py` into `providers/ollama.py` as `chat()`. Change
`tool_dispatch` to expose `dispatch()` returning `Executed`, using a
pass-through guard. Default model becomes `qwen2.5:7b`.

**Acceptance criteria:**
- [ ] With a fake adapter, `send` returns a plain answer, and handles one tool
      call, then an answer, and several tool calls in one reply
- [ ] A second `send` includes the first exchange in the messages sent to the adapter
- [ ] `Turn.tool_calls` lists every call with its arguments and result

**Verification:**
- [ ] `uv run pytest tests/test_agent_core.py -q`
- [ ] `uv run pytest -q` (existing tests still pass)

**Dependencies:** Task 1
**Files:** `agent_core.py`, `providers/__init__.py`, `providers/ollama.py`,
`tool_dispatch.py`, `tests/test_agent_core.py`
**Scope:** M

---

## Task 3: Tool-use eval script and model comparison

**Description:** `scripts/eval_tool_use.py` runs 10 fixed prompts through
`Session.send` against real Ollama. For each prompt it records which tool was
called and whether the arguments were valid. Pull `qwen2.5:7b` and
`llama3.1:8b`, run the eval on both, and save one raw reply per model as a test
fixture.

**Acceptance criteria:**
- [ ] Script prints a pass/fail line per prompt and a total score
- [ ] Results for both models recorded in `tasks/eval-results.md`
- [ ] Default model confirmed, or changed with the reason written down

**Verification:**
- [ ] Manual: `uv run python scripts/eval_tool_use.py` with each `OLLAMA_MODEL`
- [ ] Target: at least 8 of 10 for the chosen model (spec criterion 5). If
      missed, stop and review with the user.

**Dependencies:** Task 2
**Files:** `scripts/eval_tool_use.py`, `tasks/eval-results.md`,
`tests/fixtures/ollama_*.json`
**Scope:** S

---

## Checkpoint A0: model is good enough
- [ ] `uv run pytest -q` passes
- [ ] Eval results reviewed with user: keep `qwen2.5:7b`, switch models, or
      revise the plan (for example, simpler tool schemas) before Task 4

---

## Task 4: Robustness for 7B models

**Description:** Bad JSON or wrong-type arguments and unknown tool names go back
to the model as an error result. Cap each turn at 8 tool iterations. Ollama
connection refused or a 60 s timeout returns a `Turn` with the "start Ollama"
error. Keep the last 10 turns of history, truncate tool results over 6,000
characters, and set `num_ctx` to 8192. Replace `print` with `logging`.

**Acceptance criteria:**
- [ ] Malformed arguments and unknown tools produce an error tool result and the
      loop continues
- [ ] Iteration cap and Ollama down each return a `Turn` with `error` set; no
      exception, no Claude call
- [ ] History trimming and truncation covered by tests

**Verification:**
- [ ] `uv run pytest tests/test_agent_core.py -q`

**Dependencies:** Task 2
**Files:** `agent_core.py`, `providers/ollama.py`, `tests/test_agent_core.py`
**Scope:** S

---

## Task 5: CLI on `Session`; delete router

**Description:** `main.py` keeps one `Session` and prints `Turn.text` or
`Turn.error`. Delete `router.py`, drop `LLM_PROVIDER`, delete
`ollama_agent.py`, and switch `prompts.py` to the system timezone. Update the
README architecture and env sections.

**Acceptance criteria:**
- [ ] `router.py`, `ollama_agent.py`, and every `LLM_PROVIDER` reference are gone
- [ ] Prompt shows the local timezone, not a hard-coded one
- [ ] README describes Ollama-first with Claude on request

**Verification:**
- [ ] `uv run pytest -q`
- [ ] Manual: `uv run python main.py` with `ANTHROPIC_API_KEY` empty: a
      two-turn Notes conversation where turn 2 uses turn 1's context
      (spec criterion 2)
- [ ] Manual: stop Ollama; the CLI shows the start message within 2 s
      (spec criterion 4)

**Dependencies:** Tasks 3, 4
**Files:** `main.py`, `router.py`, `ollama_agent.py`, `prompts.py`, `README.md`
**Scope:** M

---

## Checkpoint A: local-only chat works
- [ ] `uv run pytest -q` passes
- [ ] Spec criteria 2 and 4 verified by hand
- [ ] Review with user before Phase 2

---

## Task 6: Claude adapter

**Description:** Move the API call from `agent.py` into `providers/claude.py`
as `chat()`. Convert neutral history (with synthetic ids) into Claude messages
containing `tool_use` and `tool_result` blocks. Delete `agent.py`.

**Acceptance criteria:**
- [ ] Conversion of a history with tool calls matches the expected Claude
      message fixture
- [ ] `agent.py` is gone; nothing imports it

**Verification:**
- [ ] `uv run pytest tests/test_providers.py -q`

**Dependencies:** Task 2
**Files:** `providers/claude.py`, `agent.py`, `tests/test_providers.py`,
`tests/fixtures/claude_history.json`
**Scope:** S

---

## Task 7: `Session.escalate` with per-request cloud consent

**Description:** `escalate(turn_id)` rebuilds the history up to that user
message, adds the Ollama turn's tool records (without its final text), and runs
the loop with the Claude adapter and `cloud_consent=True`. The returned turn
replaces the Ollama turn. In `tool_dispatch`, replace `APPLE_NOTES_ALLOW_CLOUD`
with the consent check and add `CLAUDE_ESCALATION_ENABLED`. CLI `/claude`
escalates the last turn.

**Acceptance criteria:**
- [ ] Claude receives earlier tool results and not Ollama's text; tools that
      already ran aren't run again
- [ ] Personal-data tools called by Claude without consent are rejected;
      escalation while disabled raises an error
- [ ] The escalated turn replaces the original in later `send` history

**Verification:**
- [ ] `uv run pytest -q`
- [ ] Manual: `/claude` in the CLI gives a Claude answer and the logs show no
      repeated tool calls (spec criterion 3)

**Dependencies:** Tasks 5, 6
**Files:** `agent_core.py`, `tool_dispatch.py`, `main.py`,
`tests/test_agent_core.py`, `tests/test_notes.py`
**Scope:** M

---

## Task 8: Pause and resume

**Description:** When `dispatch` returns `NeedsApproval`, the loop stops and
returns a `Turn` with `pending` set. `resume(turn_id, approved)` runs the tool,
or sends "User declined", then continues the loop. This works for both Ollama
and Claude turns. The CLI shows the pending action and asks y/n. Tested with a
fake guard.

**Acceptance criteria:**
- [ ] Approved: the tool runs once and the loop finishes the reply
- [ ] Declined: the model gets `{"success": false, "error": "User declined"}`
      and finishes the reply
- [ ] Resuming an unknown or already-finished turn raises a clear error

**Verification:**
- [ ] `uv run pytest tests/test_agent_core.py -q`

**Dependencies:** Task 5 (Task 7 too, if done in order)
**Files:** `agent_core.py`, `tool_dispatch.py`, `main.py`, `tests/test_agent_core.py`
**Scope:** M

---

## Checkpoint B: module complete
- [ ] `uv run pytest -q` passes
- [ ] All six spec success criteria met
- [ ] README updated; `CAPABILITY-MAP.md` marks `agent-core` done
- [ ] Review with user before starting `action-guard`
