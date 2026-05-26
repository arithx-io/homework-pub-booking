# Ex9 - Reflection

> Questions per `ASSIGNMENT.md` Ex9. Citations point to artifacts
> committed under `sessions/` in this repo.

## Q1 - Planner handoff decision

### Your answer

The planner in my Ex7 session never assigned work to the structured
half. Both planner tickets in `sess_1d066b03335a` produce a single
loop subgoal. The literal field reads `"assigned_half": "loop"` in
both rounds:

- `logs/tickets/tk_79f1774e/raw_output.json` (round 1): `{"id": "sg_1",
  "description": "find venue near haymarket for 12", "assigned_half":
  "loop", ...}`
- `logs/tickets/tk_da11db74/raw_output.json` (round 2): `{"id": "sg_1",
  "description": "retry with larger venue after rejection",
  "assigned_half": "loop", ...}`

The handoff happens inside the executor loop, not at the planner.
Round 1 of `logs/trace.jsonl`: the executor calls `venue_search(near=
"Haymarket", party_size=12, budget_max_gbp=2000)`. That call returns
`0 result(s)`. Haymarket Tap only has 8 seats, and party_size=12
doesn't match. The next executor event still calls
`handoff_to_structured` with a Haymarket Tap payload anyway, with
reason: *"loop half identified a candidate venue; passing to
structured half for confirmation under policy rules."* The handoff
fired even though the prior venue_search returned nothing.

That works out fine. The structured half
rejects with `party_too_large` (visible as `session.state_changed
from=structured to=loop round=1`), the bridge produces a reverse
handoff, and round 2 recovers with party 6 at The Royal Oak
(`BK-B7655866`). The loop produced a bad proposal; the structured
half and bridge transitions caught it before any commit. That's the
boundary doing its job.

### Citation

- `sessions/examples/ex7-handoff-bridge/sess_1d066b03335a/logs/trace.jsonl`
  round 1 `venue_search` (0 results), `handoff_to_structured`, and
  `session.state_changed` events.
- `sessions/examples/ex7-handoff-bridge/sess_1d066b03335a/logs/tickets/tk_8f86c41e/`
  round 1 executor ticket; raw_output.json records the zero-result
  search and the subsequent handoff inside the same subgoal.
- `sessions/examples/ex7-handoff-bridge/sess_1d066b03335a/logs/handoffs/round_1_forward.json`
  archived round-1 handoff payload (Haymarket Tap, party=12) after
  the structured half rejected.
- `sessions/examples/ex7-handoff-bridge/sess_1d066b03335a/ipc/handoff_to_structured.json`
  final live handoff payload (Royal Oak, party=6) from round 2.

---

## Q2 - Dataflow integrity catch

### Your answer

The committed Ex5 session `sess_eff9faaddd54` shows the validator
running on a clean flyer. The trace records three producer calls
before the flyer is written. `get_weather` returns `cloudy` and `12C`.
`calculate_cost(haymarket_tap, 6)` returns `total £356` and `deposit
£71`. `generate_flyer` writes `workspace/flyer.html`. The flyer
contains exactly those facts, so `verify_dataflow` reports
`dataflow OK: verified 6 fact(s) against tool outputs` (the extra
two are the venue name "Haymarket Tap" and its address, picked up by
the named-entity extractor and verified against the venue_search
output).

The check is designed for fabrications that look plausible. Try
swapping `£356` for `£9999` in the committed flyer. All three numbers
read like credible pub totals at a glance. Trying with `£540` (the
older FakeLLM-scripted value from before the cohort fix) is
sneakier still, because it looks like a real cost that the system
might have produced on an earlier run. The validator doesn't reason
about plausibility. It extracts money, temperature, weather-condition,
and venue-name facts from the rendered flyer, then checks whether each
appears in a producer tool's output. `calculate_cost` produced 356
and 71, not 9999 or 540, so the planted value gets flagged.

I had to fix the validator to ignore
`generate_flyer` as a source. The starter version scanned both
output and arguments across every record. That meant a planted value
in `generate_flyer`'s argument log would "verify" itself. Excluding
the renderer plus the in-tool sanitisation (log only argument keys,
never values) closes the loop. The dataflow probe in `grader/` plants
three values per run: an obvious-price fabrication (`£9999`), a
nonexistent venue name (`Castle Royal Grand Inn`), and an impossible
temperature phrase (`scorching 35C`). After the producer-output
restriction and the named-entity extractor, the probe reports 6/6
caught.

### Citation

- `sessions/examples/ex5-edinburgh-research/sess_eff9faaddd54/logs/trace.jsonl`
  `venue_search`, `get_weather`, `calculate_cost`, `generate_flyer`,
  `complete_task` events.
- `sessions/examples/ex5-edinburgh-research/sess_eff9faaddd54/workspace/flyer.html`
  the verified flyer (£356, £71, cloudy, 12°C, Haymarket Tap).
- `starter/edinburgh_research/integrity.py`:
  `_fact_appears_in_producer_output` (the producer-only check),
  `extract_named_entity_facts`, `extract_temperature_facts`.
- `starter/edinburgh_research/tools.py`: `generate_flyer` logs only
  argument keys, never values, so the validator can't self-verify.

---

## Q3 - Production failure & primitive that surfaces it

### Your answer

My failure mode is the ticket state machine reporting success while
the actual goal was never produced. I caught this in a live
`make ex5-real` run (planner Qwen3-Next-80B, executor Qwen3-32B via
Nebius). Session `sess_c0916c8406f0`.

The planner emitted three subgoals, all assigned to the loop half.
The executor for sg_1 then called `venue_search` four times with
the wrong arguments. Never `near="Haymarket", party_size=6` as the
task required. Lines 3–6 of `logs/trace.jsonl` show party sizes
10, 20, 15, and 20 against locations the executor invented (`"Old
Town, Edinburgh"`, `"Princes Street, Edinburgh"`, `"Edinburgh City
Centre"`). All four returned `0 result(s)`. After giving up, the
executor abandoned `generate_flyer` and called `write_file` instead,
with hallucinated content: "The Scotch Whisky Experience, The
Edinburgh Dungeon, The Royal Botanic Garden..." None of those are
pubs and none appear in `sample_data/venues.json`. The file landed
at `workspace/workspace/venues_list.txt` because the executor used a
relative path from inside the workspace directory.

The primitive is the ticket state machine. The executor ticket
`tk_a2f19e9c/state.json` reports `state: "success"`. The summary
even reads: *"Executor completed subgoal sg_1 in 6 turn(s). Made 5
tool call(s)."* A monitor that watches only ticket-level state would
have flagged this run as healthy. But the same primitive surfaces
the failure once you ask the right question of the same data. The
ticket lists the tool calls made (`venue_search × 4, write_file × 1`),
and a deterministic check like "did this run produce a generate_flyer
ticket?" or "did session.state reach complete?" catches the
mismatch. Session.state stayed `"executing"` with `result: null`. No
flyer at `workspace/flyer.html`. The ticket reports success because
from the executor's local view, five tool calls returned `success:
true`. Tickets are the primitive because they make the disagreement
between operation success and goal achievement queryable from
durable evidence.

### Citation

- `sessions/examples/ex5-edinburgh-research/sess_c0916c8406f0/logs/trace.jsonl`
  4× wrong-arg `venue_search` (all 0 results), then `write_file`
  with hallucinated content. No `generate_flyer`, no `complete_task`.
- `sessions/examples/ex5-edinburgh-research/sess_c0916c8406f0/logs/tickets/tk_a2f19e9c/state.json`
  executor ticket reports `state: "success"` despite no flyer produced.
- `sessions/examples/ex5-edinburgh-research/sess_c0916c8406f0/logs/tickets/tk_a2f19e9c/summary.md`
  *"Executor completed subgoal sg_1 in 6 turn(s). Made 5 tool call(s)."*
- `sessions/examples/ex5-edinburgh-research/sess_c0916c8406f0/session.json`
  final state `"executing"`, result `null`.
- `sessions/examples/ex5-edinburgh-research/sess_c0916c8406f0/workspace/workspace/venues_list.txt`
  hallucinated venues written to the wrong file at the wrong path.
- Healthy contrast: `sessions/examples/ex7-handoff-bridge/sess_1d066b03335a/logs/tickets/`
  has 4 tickets across 2 rounds (2 planner.plan + 2 executor.run_subgoal),
  all consistent with `session.state` reaching `complete`.
- `starter/edinburgh_research/tools.py`: `_spiral_check` defensive
  in-tool guard (threshold > 3 returns a cached result with an explicit
  STOP hint).
