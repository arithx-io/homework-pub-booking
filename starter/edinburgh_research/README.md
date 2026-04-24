# Ex5 — Edinburgh research scenario

**You are building:** a complete loop-half scenario that plans, researches, and
produces a flyer for an Edinburgh pub event. Plus a dataflow integrity check
that catches LLM fabrication.

**Spec:** see `ASSIGNMENT.md` §Ex5 for the full grading breakdown.

**Time estimate:** 3-5 hours.

## Files in this directory

| File | What it is | Your job |
|---|---|---|
| `run.py` | The scenario entrypoint — builds planner + executor, runs them | Fill in the TODOs where the scaffold wires up tools and runs the loop |
| `tools.py` | Four tool implementations | Implement each tool; each must log to `_TOOL_CALL_LOG` |
| `integrity.py` | The dataflow check | Implement `verify_dataflow()` |
| `sample_data/` | Fixture JSON the tools read from | **Do not modify** — the grader plants failures here |

## How to run

Offline (default — uses FakeLLMClient, zero tokens):

```
make ex5
```

Against a real LLM (burns Nebius tokens):

```
make ex5-real
```

Both modes should END with a dataflow check; both should produce a session
directory you can inspect.

## Expected trajectory

1. Planner produces 2 subgoals: "research venues + weather" and "write flyer".
2. Executor runs `venue_search`, `get_weather`, `calculate_cost` in parallel
   (all marked `parallel_safe=True`), then `generate_flyer` alone (not
   parallel-safe because it writes).
3. After completion, `verify_dataflow` reads the flyer and checks every
   concrete fact against `_TOOL_CALL_LOG`.
4. If any fact didn't come from a tool call, the run fails with a clear
   report.

## Common mistakes

- **Forgetting to log tool calls**: if a tool runs but doesn't append to
  `_TOOL_CALL_LOG`, `verify_dataflow` can't verify its outputs. Every tool
  body should open with the logging call.
- **Making `generate_flyer` parallel-safe**: writes must never be parallelised.
  The grader checks for this explicitly.
- **Having `verify_dataflow` return too leniently**: if it always passes,
  the grader's planted failure won't trigger. If it always fails, your
  legitimate runs break. Find the right balance: exact-string match for
  numeric values, case-insensitive substring for names.
