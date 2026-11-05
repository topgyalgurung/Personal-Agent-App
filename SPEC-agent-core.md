# Spec: agent-core

Module of [CAPABILITY-MAP.md](CAPABILITY-MAP.md). Status: **approved 2026-11-05**.

## Objective

Replace today's "Claude first, Ollama on failure" router with a chat engine that:

1. Answers every message with the **local Ollama model**, using tool calls.
2. Remembers the conversation across turns. Today every message starts fresh.
3. Re-answers a turn with **Claude only when the user asks** ("Ask Claude
   instead"), using the same conversation and the tool results already fetched.
4. Can **pause** a turn when a tool call needs approval and **resume** it after
   the user approves or rejects. `action-guard` decides which calls pause.
   `agent-core` only provides the pause and resume mechanism.

Every other module calls into `agent-core`: the CLI now, `chat-api` later.

### User stories

- When I ask "what's in my notes about the trip?", the local model searches and
  reads my notes and answers. Nothing leaves my laptop.
- When I follow up with "and what did I say about the budget?", it knows "the
  trip" from the earlier turn.
- When the local answer is bad, I ask Claude to redo that turn and get a better
  answer. Actions that already ran (for example, a note that was created) are
  not repeated.
- When Ollama isn't running, I get a plain message telling me how to start it.
  Nothing switches to Claude silently.

## Tech Stack

- Python 3.14 (from `pyproject.toml`), managed with `uv`
- Ollama REST `/api/chat` called with `requests` (as today). The default model
  changes from `qwen3:4b` to **`qwen2.5:7b`**, configurable with `OLLAMA_MODEL`.
- `anthropic` SDK for escalation. The default `CLAUDE_MODEL` stays configurable.
- pytest. No new dependencies.

## Design

### Public interface (`agent_core.py`)

```python
@dataclass
class Turn:
    id: str
    provider: Literal["ollama", "claude"]
    text: str                       # final answer ("" while paused)
    tool_calls: list[ToolRecord]    # every call made in this turn, with results
    pending: PendingAction | None   # set when paused for approval
    error: str | None = None        # user-facing error, e.g. Ollama down


class Session:
    def send(self, user_text: str) -> Turn: ...
    def resume(self, turn_id: str, approved: bool) -> Turn: ...
    def escalate(self, turn_id: str) -> Turn: ...
```

- `send`: runs the Ollama tool loop for a new user message.
- `resume`: continues a paused turn. If approved, the pending tool runs. If
  rejected, the model receives `{"success": false, "error": "User declined"}`
  and finishes its reply.
- `escalate`: re-answers turn `turn_id` with Claude. Claude gets the history up
  to and including that user message, **plus the Ollama turn's tool calls and
  results**, but **not** Ollama's final text. Claude may call more tools, and
  those go through the same guard. The returned turn replaces the Ollama turn in
  the history.

### Tool-call seam with `action-guard`

```python
def dispatch(name, arguments, *, provider, cloud_consent) -> Executed | NeedsApproval
```

Until `action-guard` is built, a pass-through guard always returns `Executed`.
This module defines the seam and its tests. `action-guard` fills in the rules.

### Conversation state

- History is stored in **one provider-neutral format** (role, text, tool
  calls, tool results) and converted to Ollama or Claude format at call time.
  That is what lets `escalate` reuse a turn.
- History lives in memory, one `Session` per process. It is not saved across
  restarts in v1.
- Context budget for a 7B model: send the system prompt plus the **last 10
  turns**. Truncate any single tool result over **6,000 characters** and add a
  `[truncated]` marker. Set Ollama `num_ctx` to 8192.

### Privacy

- Ollama must be a local endpoint. Keep the existing `localhost` and `:cloud`
  checks.
- Remove the global `APPLE_NOTES_ALLOW_CLOUD` switch. Personal data (notes,
  email, calendar) can reach Claude **only** inside an `escalate` call, which
  passes `cloud_consent=True` to dispatch. Any other Claude path is rejected.
- `CLAUDE_ESCALATION_ENABLED=0` turns off escalation entirely. `escalate`
  raises an error and the UI hides the button.

### Robustness (aimed at 7B models)

- Malformed tool arguments (bad JSON, wrong types) or an unknown tool name: send
  the error back to the model as a tool result so it can retry. Do not crash.
- At most **8 tool iterations** per turn. After that, return a turn with an
  error and whatever tools ran.
- Ollama connection refused or timeout (60 s): return a turn with
  `error="Ollama isn't running. Start it with: ollama serve"`. No fallback.
- Replace `print` calls with `logging`. Tool activity is available through
  `Turn.tool_calls`.
- The system prompt uses the **system timezone** instead of the hard-coded
  `America/New_York`.

### Removed or changed

- `router.py`: delete it. Automatic fallback goes against the confirmed intent.
- `agent.py` and `ollama_agent.py` become thin provider adapters under
  `agent_core`: one function that sends messages and returns the reply.
- `main.py`: the CLI uses `Session`. Type `/claude` to escalate the last turn
  and `y`/`n` to answer a pending action.
- `LLM_PROVIDER` env var: removed.

## Commands

```
Setup:      uv sync && ollama pull qwen2.5:7b
Run (CLI):  uv run python main.py
Test:       uv run pytest -q
Test one:   uv run pytest tests/test_agent_core.py -q
Eval:       uv run python scripts/eval_tool_use.py     # needs Ollama running
```

## Project Structure

```
agent_core.py           → Session, Turn, tool loop, history, escalation
providers/ollama.py     → Ollama adapter (from ollama_agent.py)
providers/claude.py     → Claude adapter (from agent.py)
tool_dispatch.py        → dispatch() seam, registry, privacy checks
schemas.py, prompts.py  → unchanged location
main.py                 → CLI on top of Session
tests/test_agent_core.py
scripts/eval_tool_use.py
```

Flat layout at the root, matching today's code (decided, see Decisions).

## Code Style

Match the existing code: small functions, docstrings, plain dicts at the
edges, early returns, explicit errors.

```python
def run_tool_loop(history, adapter, *, provider, cloud_consent=False):
    """Call the model until it answers or a tool needs approval."""
    for _ in range(MAX_TOOL_ITERATIONS):
        reply = adapter.chat(history.for_provider(provider))
        history.add_assistant(reply)

        if not reply.tool_calls:
            return Turn.answered(provider, reply.text, history.turn_tools())

        for call in reply.tool_calls:
            outcome = dispatch(
                call.name, call.arguments,
                provider=provider, cloud_consent=cloud_consent,
            )
            if isinstance(outcome, NeedsApproval):
                return Turn.paused(provider, outcome.action, history.turn_tools())
            history.add_tool_result(call, outcome.result)

    return Turn.failed(provider, "Too many tool steps.", history.turn_tools())
```

- `snake_case` functions, `PascalCase` dataclasses, `UPPER_CASE` constants.
- Tool results are always JSON-serializable dicts with a `success` key.
- No bare `except:`. Catch specific errors at provider boundaries.

## Testing Strategy

- **Unit tests (pytest), no network:** fake adapters return scripted replies.
  They cover:
  - a plain answer
  - one tool call, then an answer
  - multiple tool calls in one reply
  - malformed arguments, then a retry
  - an unknown tool
  - the iteration cap
  - Ollama down, giving a friendly error
  - history carried across `send` calls
  - pause, then `resume(approved=True)` runs the tool
  - pause, then `resume(approved=False)` sends "declined"
  - `escalate` passes tool results without Ollama's text and does not re-run
    tools that already ran
  - `escalate` while disabled raises an error
  - personal-data tools called by Claude without consent are rejected
  - history trimming and tool-result truncation
- **Adapter tests:** convert history to Ollama and Claude message formats,
  checked against fixture JSON.
- **Eval script (manual, real Ollama):** 10 fixed prompts, for example
  "list my notes about X" or "what's due today". It checks that the expected
  tool is called with valid arguments. This measures local model quality. It is
  not a CI gate.
- Existing `tests/test_agent.py` and `tests/test_notes.py` keep passing.

## Boundaries

- **Always:** run `uv run pytest -q` before saying a task is done; send personal
  data to Claude only through `escalate`; keep the local-endpoint check on Ollama.
- **Ask first:** adding a dependency; moving code into `src/`; changing the tool
  schema format in `schemas.py`; changing the default model.
- **Never:** automatic fallback to Claude; logging note, email, or calendar
  contents at INFO level or above; committing `.env` or API keys; deleting
  failing tests to get to green.

## Success Criteria

1. `uv run pytest -q` passes, including every case in Testing Strategy.
2. In the CLI with Ollama running and Claude unset (`ANTHROPIC_API_KEY` empty),
   a two-turn conversation about Notes works, and the second turn uses context
   from the first.
3. `/claude` on a turn produces a Claude answer. Logs show no tool already run
   in that turn being called again.
4. With Ollama stopped, the CLI shows the "start Ollama" message within 2 s and
   makes no Claude call.
5. The eval script reaches **at least 8 of 10** correct tool selections with
   `qwen2.5:7b`. If not, record the result and revisit the model choice before
   `action-guard`.
6. `router.py` and the `LLM_PROVIDER` env var are gone. The README architecture
   section is updated.

## Decisions (resolved 2026-11-05)

1. **Package layout:** stay flat at the root for v1.
2. **Escalated turn:** the Claude answer replaces the Ollama answer in the
   history. The UI does not keep both.
3. **Model:** default `qwen2.5:7b`. Pull `llama3.1:8b` too and let the eval
   script decide.
4. **Fake tasks and calendar in `tools.py`:** keep them until the Google modules
   replace them.
