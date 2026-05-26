# Ex7 - Handoff bridge

## Your answer

`HandoffBridge.run()` does up to `max_rounds=3` loop↔structured round
trips. Each round:

1. Emit `bridge.round_start` with `{round: N, half: "loop"}`.
2. Run `loop_half.run(session, current_input)`. If
   `next_action="complete"`, mark the session complete and return. If
   `next_action="handoff_to_structured"`, continue.
3. Build a `Handoff` via `build_forward_handoff()`, write it via
   `write_handoff()` (lands at `ipc/handoff_to_structured.json`),
   emit `session.state_changed {from: loop, to: structured, round: N}`.
4. Run `structured_half.run(session, {"data": handoff.data})`. If
   `next_action="complete"`, mark complete; if `"escalate"`, build a
   reverse task and continue.

Fail-closed IPC discipline: before round N+1 runs, the bridge moves
the previous forward handoff to `logs/handoffs/round_N_forward.json`.
At most one live handoff file ever sits in `ipc/`, and the audit
trail is preserved. (`write_handoff()` writes to `session.ipc_dir`,
not `ipc_input_dir`; I caught and fixed a path bug here early on.)

**Tier 1 (mock), `sess_1d066b03335a`.** Round 1 starts with party 12
near Haymarket. `venue_search(near='Haymarket', party_size=12)`
returns zero results (Haymarket Tap only has 8 seats). The executor
calls `handoff_to_structured` with a Haymarket Tap payload anyway.
The structured half rejects with `party_too_large`, and the bridge
returns control to the loop instead of committing a bad booking.
Round 2 re-runs with the rejection reason in context, proposes party
6 at The Royal Oak, and the structured half confirms
(`BK-B7655866`). Session reaches `complete` in two rounds.

I added the `ex7-real` Makefile target. Upstream had `ex5-real` and
`ex6-real` patterns but not Ex7.

**Tier 2 (live Rasa), `sess_c778f14fb817`.** Same scenario against a
live Rasa Pro server. Identical 2-round trajectory: round 1
`Reason: party_too_large` parsed from the live `utter_booking_rejected`
text reply (using the text-fallback parser from Ex6), round 2
confirmed `BK-B7655866`. Confirms the bridge state machine and IPC
archive work identically against mock and live structured halves.
Only the response parser path differs by tier.

## Citations

- `sessions/examples/ex7-handoff-bridge/sess_1d066b03335a/logs/trace.jsonl`:
  mock-mode round-trip (round 1 rejection, round 2 completion).
- `sessions/examples/ex7-handoff-bridge/sess_1d066b03335a/logs/handoffs/round_1_forward.json`:
  archived round-1 handoff (Haymarket Tap, party_size=12).
- `sessions/examples/ex7-handoff-bridge/sess_1d066b03335a/ipc/handoff_to_structured.json`:
  final live handoff (The Royal Oak, party_size=6).
- `sessions/examples/ex7-handoff-bridge/sess_1d066b03335a/logs/tickets/tk_8f86c41e/`:
  round 1 executor ticket; `tk_1503b962` is round 2.
- `sessions/examples/ex7-handoff-bridge/sess_c778f14fb817/logs/trace.jsonl`:
  live-Rasa run, same 2-round trajectory, `BK-B7655866`.
- `starter/handoff_bridge/bridge.py`: bounded round-trip state machine
  plus the corrected IPC cleanup (`session.ipc_dir`, not `ipc_input_dir`).
- `Makefile`: added `ex7-real` target.
