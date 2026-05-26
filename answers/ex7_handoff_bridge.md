# Ex7 — Handoff bridge

## Your answer

`HandoffBridge.run()` orchestrates up to `max_rounds=3` loop↔structured
round trips. Each round:
1. Emit `bridge.round_start` with `{round: N, half: "loop"}`.
2. Run `loop_half.run(session, current_input)`. If
   `next_action="complete"`, mark session complete and return. If
   `"handoff_to_structured"`, continue.
3. Build a `Handoff` via `build_forward_handoff()`, `write_handoff()`
   to `ipc/input/handoff_to_structured.json`, emit
   `session.state_changed {from: loop, to: structured, round: N}`.
4. Run `structured_half.run(session, {"data": handoff.data})`. If
   `next_action="complete"`, mark session complete; if `"escalate"`,
   build a reverse task and continue the loop.

**Fail-closed IPC discipline.** Before round N+1's loop runs, the
bridge moves `ipc/input/handoff_to_structured.json` to
`logs/handoffs/round_N_forward.json`. This enforces the
ASSIGNMENT.md §Ex7 rubric "at most one handoff file visible in
`ipc/` at any time" and creates an audit trail for the structured
half's history. Without this, a partial failure between structured
rejection and the next loop's `loop_half.run` would leave stale
forward data in `ipc/` that the next round might mis-route.

**End-to-end evidence (session `sess_7141e7342034`).**
- Round 1: planner produced 1 subgoal (`1 to loop, 0 to structured`).
  Executor called `venue_search(near='Haymarket', party_size=12)`
  then `handoff_to_structured` with `reason: "loop half identified
  a candidate venue; passing to structured half for confirmation
  under policy rules"`. Structured (mock Rasa) rejected with
  `party_too_large` (12 > cap 8).
- Round 2: planner re-ran with the rejection reason in context,
  executor downsized to `party_size=6` at Royal Oak (16 seats).
  Structured confirmed: `BK-B7655866`.

The party-size downsize from 12→6 in round 2 is intentional per
Mosokina's clarification in Discord (May 22): the loop is expected
to reformulate after a rejection, not just retry the same args at
a different venue.

**Added `ex7-real` Makefile target.** Upstream Makefile had `ex5-real`
and `ex6-real` but not `ex7-real`. The cohort consensus (Andrey's
follow-up + my own implementation) was that `make ex7-real` should
mirror the pattern — added it as a one-line `--real` wrapper.

## Citations

- `sessions/examples/ex7-handoff-bridge/sess_7141e7342034/logs/trace.jsonl`
  — 2× bridge.round_start, 4× session.state_changed (including round-1
  rejection `reason: party_too_large`), 4× executor.tool_called
- `sessions/examples/ex7-handoff-bridge/sess_7141e7342034/logs/tickets/tk_722c30e4/summary.md`
  ("Executor completed subgoal sg_1 in 2 turn(s). Made 2 tool call(s):
  venue_search, handoff_to_structured. Handoff to structured half
  requested.")
- `sessions/examples/ex7-handoff-bridge/sess_7141e7342034/ipc/handoff_to_structured.json`
  — final forward payload, round 2
- `starter/handoff_bridge/bridge.py` — `HandoffBridge.run`,
  `build_forward_handoff`, `build_reverse_task`
- `Makefile:312` — `ex7-real` target I added
