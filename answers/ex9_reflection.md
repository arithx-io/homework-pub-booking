# Ex9 — Reflection

> Questions per `ASSIGNMENT.md` Ex9. All citations below point to artifacts
> already committed under `sessions/` in this repo.

## Q1 — Planner handoff decision

### Your answer

Strictly, my Ex7 logs do **not** show the planner assigning work directly
to the structured half. In `sess_057c0d8139e6`, the planner emits one
loop subgoal per round; the actual handoff is an executor-level action
inside that loop. The relevant point is round 1 of `logs/trace.jsonl`:
the executor first calls `venue_search` with `near="Haymarket"`,
`party_size=12`, and `budget_max_gbp=2000`. **That call returns
`0 result(s)`** — Haymarket Tap has 8 seats; party_size=12 doesn't
match. The next executor event still calls `handoff_to_structured`
with a Haymarket Tap payload and the explicit reason: *"loop half
identified a candidate venue; passing to structured half for
confirmation under policy rules."*

This is worth naming precisely. The signal was not a clean planner
`assigned_half="structured"` field; it was the executor deciding the
booking data should be adjudicated by the rule-bound half. The trace
also exposes a semantic weakness: the first handoff was not
well-supported by the immediately preceding `venue_search` result
because that result had `count=0`. The structured half then did its
job anyway: it rejected the proposal with `party_too_large`
(`session.state_changed from=structured to=loop round=1`), and the
bridge produced a reverse handoff back to the loop. Round 2 shows
recovery: the loop proposes a smaller party at The Royal Oak and the
structured half moves the session to complete (BK-B7655866). This
makes the architectural lesson sharper — the loop can produce
imperfect proposals, so the structured half and the bridge's state
transitions are not optional; they are the safety boundary.

### Citation

- `sessions/examples/ex7-handoff-bridge/sess_057c0d8139e6/logs/trace.jsonl`
  — round 1 `venue_search` (0 result(s)), `handoff_to_structured`,
  `session.state_changed` events (rejection reason `party_too_large`).
- `sessions/examples/ex7-handoff-bridge/sess_057c0d8139e6/logs/tickets/tk_17971d20/`
  — round 1 executor ticket; raw_output.json records the
  zero-result `venue_search` AND the subsequent `handoff_to_structured`
  call inside the same subgoal.
- `sessions/examples/ex7-handoff-bridge/sess_057c0d8139e6/logs/handoffs/round_1_forward.json`
  — the archived round-1 handoff payload (Haymarket Tap, party=12)
  preserved after the structured half rejected.
- `sessions/examples/ex7-handoff-bridge/sess_057c0d8139e6/ipc/handoff_to_structured.json`
  — final live handoff payload (Royal Oak, party=6) from round 2.

---

## Q2 — Dataflow integrity catch

### Your answer

The committed Ex5 session `sess_df01eee6ce9e` is the clean run after
fixing the dataflow problem. It shows why the integrity check matters.
The trace records three factual producer calls before flyer generation:
`get_weather` returns `cloudy` and `12C`; `calculate_cost(haymarket_tap,
6)` returns `total £356` and `deposit £71`; then `generate_flyer`
writes `workspace/flyer.html`. The final flyer contains exactly those
primitive facts: weather `cloudy`, temperature `12°C`, total `£356`,
and deposit `£71`. `verify_dataflow` therefore reports
`dataflow OK: verified 4 fact(s) against tool outputs`.

The failure this check is designed to catch is a flyer that looks
plausible but contains a value no tool produced. A concrete planted
case is to edit the committed flyer and change `£356` to `£9999`, or
back to the older scripted `£540` from the upstream FakeLLM script.
Manual inspection might miss it because all three are syntactically
plausible money amounts in a pub-booking flyer. The integrity check
does not rely on plausibility: it extracts money, temperature, and
weather-condition facts from the rendered flyer, then checks whether
each scalar appears in the tool-call log. In the committed trace,
`calculate_cost` produced `356` and `71`, not `9999` and not `540`,
so the planted amount would be reported as an unverified fact. That
is the core value of the exercise — the validator compares the final
artifact against actual tool outputs, not against the LLM's
confidence or a human reviewer's intuition.

A related fix I applied during Ex5 development: `generate_flyer`
itself records to `_TOOL_CALL_LOG` (the docstring requires it), but
only with sanitised metadata (`{path, bytes_written}` + arg *keys*) —
never the rendered fact values. Without this, `verify_dataflow` could
self-validate the flyer against the flyer-tool's own log entry
(circular validation bug Gareth flagged in Discord).

### Citation

- `sessions/examples/ex5-edinburgh-research/sess_df01eee6ce9e/logs/trace.jsonl`
  — `venue_search`, `get_weather`, `calculate_cost`, `generate_flyer`,
  `complete_task` events.
- `sessions/examples/ex5-edinburgh-research/sess_df01eee6ce9e/workspace/flyer.html`
  — final flyer facts (£356, £71, cloudy, 12°C).
- `starter/edinburgh_research/integrity.py` — fact extraction and
  `verify_dataflow` implementation.
- `starter/edinburgh_research/tools.py` — `generate_flyer` sanitised
  log args preventing circular self-validation.

---

## Q3 — Production failure & primitive that surfaces it

### Your answer

**Failure mode**: loop spiral on venue research. In production I would
expect the loop half to repeat `venue_search` with slightly varied
arguments after a partial or disappointing result, especially under
real-LLM execution. A model can make that look like progress — change
the area, budget, or party size, call the same read tool again, then
continue burning tokens without a user-visible crash. This is worse
than a hard exception because it degrades cost and latency while still
producing a superficially normal session. The cohort has documented
this exact symptom in `docs/real-mode-failures.md`; Lucia reported it
on May 19.

**Primitive**: the ticket state machine. The useful signal is not the
model's explanation; it is the sequence of recorded operations. Every
planner and executor operation leaves a ticket under
`logs/tickets/tk_<id>/` with `manifest.json`, `raw_output.json`,
`state.json`, `summary.md`. A healthy session has a small bounded
number of research calls. A spiral session has an abnormal count of
tickets whose tool argument matches `venue_search`. That count can be
monitored deterministically with no LLM judge: alert when
`venue_search_count > 5`, or when the same tool is called repeatedly
with small argument perturbations. The committed Ex7 run gives a
healthy contrast: `sess_057c0d8139e6` has bounded round-trip behaviour,
visible bridge state transitions, and only the expected
research/handoff tickets (`tk_17971d20`, `tk_7afc5328`). In a real
pub-booking service, that is exactly the primitive I would build
operational metrics around — tickets are durable, auditable evidence
of what the agent actually did.

### Citation

- `sessions/examples/ex7-handoff-bridge/sess_057c0d8139e6/logs/tickets/`
  — bounded healthy ticket set for comparison (4 tickets across 2
  rounds: 2 planner.plan + 2 executor.run_subgoal).
- `sessions/examples/ex7-handoff-bridge/sess_057c0d8139e6/logs/trace.jsonl`
  — two bridge rounds, four state transitions, then completion.
- `starter/edinburgh_research/tools.py` — `_spiral_check` defensive
  in-tool guard (threshold > 3 returns cached result with explicit
  STOP hint).

### Q3 — alternative phrasing (older slide-deck draft)

If the question is read as *"if you could keep only one
sovereign-agent primitive, which would it be?"* — session
directories. Tickets, trace logs, IPC files, workspace artifacts,
and final answers are all inspectable because the session directory
is the unit of state. Reconstructing a failed agent run without
that directory boundary becomes archaeology.
