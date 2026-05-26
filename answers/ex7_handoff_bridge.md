# Ex7 — Handoff bridge

## Your answer

`HandoffBridge.run()` orchestrates up to `max_rounds=3` loop↔structured
round trips. Each round:

1. Emit `bridge.round_start` with `{round: N, half: "loop"}`.
2. Run `loop_half.run(session, current_input)`. If
   `next_action="complete"`, mark session complete and return. If
   `next_action="handoff_to_structured"`, continue.
3. Build a `Handoff` via `build_forward_handoff()`, write it via
   `write_handoff()` (lands at `ipc/handoff_to_structured.json`),
   emit `session.state_changed {from: loop, to: structured, round: N}`.
4. Run `structured_half.run(session, {"data": handoff.data})`. If
   `next_action="complete"`, mark session complete; if `"escalate"`,
   build a reverse task and continue.

**Fail-closed IPC discipline.** Before round N+1 runs, the bridge
moves the previous forward handoff to
`logs/handoffs/round_N_forward.json`. This keeps at most one live
handoff file visible in `ipc/` and preserves an audit trail. (Note:
the first implementation in this repo had a path bug — `ipc_input_dir`
instead of `ipc_dir` — which meant the archive logic silently skipped
the move. The cited session below was regenerated against the fixed
implementation, so `logs/handoffs/round_1_forward.json` is now
populated and `ipc/handoff_to_structured.json` holds round 2's
payload as expected.)

**End-to-end evidence (session `sess_1d066b03335a`).** Round 1 starts
with a loop request for party size 12 near Haymarket. The trace
shows `venue_search(near='Haymarket', party_size=12)` returning
**zero results** — Haymarket Tap only has 8 seats. The executor
calls `handoff_to_structured` with a Haymarket Tap payload anyway.
That is not semantically ideal, but it is useful evidence: the
structured half rejects the handoff with `party_too_large`, and the
bridge safely returns control to the loop rather than completing a
bad booking. Round 2 re-runs the loop with the rejection reason in
context, proposes party 6 at The Royal Oak, and the structured half
confirms (`BK-B7655866`). The session reaches `complete` within two
rounds.

The party-size downsize from 12→6 in round 2 is intentional per
Mosokina's clarification in Discord (May 22): the loop is expected
to reformulate after a rejection, not just retry the same args at
a different venue.

I also added an `ex7-real` Makefile target. Upstream had `ex5-real`
and `ex6-real` patterns but no equivalent for Ex7; the added target
is a one-line `--real` wrapper for consistency.

## Citations

- `sessions/examples/ex7-handoff-bridge/sess_1d066b03335a/logs/trace.jsonl`
  — round 1 rejection (party_too_large) and round 2 completion.
- `sessions/examples/ex7-handoff-bridge/sess_1d066b03335a/logs/handoffs/round_1_forward.json`
  — archived round-1 forward handoff (Haymarket Tap, party_size=12).
- `sessions/examples/ex7-handoff-bridge/sess_1d066b03335a/ipc/handoff_to_structured.json`
  — final live handoff payload (The Royal Oak, party_size=6).
- `sessions/examples/ex7-handoff-bridge/sess_1d066b03335a/logs/tickets/tk_8f86c41e/`
  — round 1 executor ticket; `tk_1503b962` is round 2.
- `starter/handoff_bridge/bridge.py` — bounded round-trip state
  machine + corrected IPC cleanup (uses `session.ipc_dir`).
- `Makefile` — added `ex7-real` target.
