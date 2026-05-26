# Ex9 — Reflection

> Questions per ASSIGNMENT.md §Ex9 (lines 216–228). All citations resolve to
> files under `sessions/` in this repo, produced by my own runs.

## Q1 — Planner handoff decision

### Your answer

In my Ex7 session `sess_7141e7342034`, the planner produced one subgoal per
round, each with `assigned_half: "loop"` — never assigning anything directly
to the structured half. The handoff was an **executor-level** decision made
inside the loop, not a planner-level subgoal routing.

The executor's second turn within subgoal `sg_1` invoked the
`handoff_to_structured` tool. The trace event records the explicit reason
(`logs/trace.jsonl`, `executor.tool_called` for round 1):

> `reason`: "loop half identified a candidate venue; passing to structured
> half for confirmation under policy rules"
> `data`: `{venue_id: "Haymarket Tap", party_size: "12", date: "2026-04-25"}`

The signal that caused the decision was the loop having gathered enough
context (a candidate venue from `venue_search`) to ask the question only
the structured half can answer: "does this booking pass the rules?" That
question — *deterministic policy enforcement* — is precisely the structured
half's job. The loop calls `handoff_to_structured` whenever it has
enriched data ready for adjudication. Tickets `tk_722c30e4` (round 1)
and `tk_74beabfa` (round 2) record this — each ends with
"Handoff to structured half requested."

The broader pattern is interesting: the **planner** treats the whole
research-and-confirm task as one loop subgoal, because exploration is
loop-shaped; the **executor** decides at runtime that part of the work
needs structured handling. The architectural split happens in
intermediate execution, not in upfront planning. That's why
`session.state_changed` events fire at the bridge level
(`from: loop → to: structured`, `round: 1`), not at the planner level.

### Citation

- `sessions/examples/ex7-handoff-bridge/sess_7141e7342034/logs/trace.jsonl`
  — `executor.tool_called` events for `handoff_to_structured` in both rounds
- `sessions/examples/ex7-handoff-bridge/sess_7141e7342034/logs/tickets/tk_722c30e4/summary.md`
- `sessions/examples/ex7-handoff-bridge/sess_7141e7342034/ipc/handoff_to_structured.json`
  — final forward payload, round 2

---

## Q2 — Dataflow integrity catch

### Your answer

My integrity check caught a real fabrication during Ex5 development — not
a planted one, an inconsistency between the FakeLLMClient's scripted
trajectory and the (cohort-corrected) `calculate_cost` formula.

Background: the upstream `run.py` scripted `total_gbp: 540` and
`deposit_required_gbp: 0` in the `event_details` passed to
`generate_flyer`. After I applied the cohort's calculate_cost fix
(`max(subtotal, min_spend)` instead of `+`), my tool returned
`total_gbp: 356, deposit_required_gbp: 71` for the same inputs
(`haymarket_tap, party=6, duration=3, bar_snacks`). The first
`make ex5` exited with:

> `dataflow FAIL: 1 unverified fact(s): ['£540']`

`verify_dataflow` extracted `£540` from the generated flyer, scanned
`_TOOL_CALL_LOG`, and found `calculate_cost` had logged 356 — not 540.
The 540 was orphan data: it appeared in the flyer's text, but no tool
call had ever produced that value. Manual inspection wouldn't have
flagged it; £540 is a plausible-looking number for six people over
three hours and the human eye doesn't cross-reference. The check did,
mechanically, by comparing the rendered fact set to ground truth in
`_TOOL_CALL_LOG`.

Fixing the FakeLLM script to use the actual computed values brought
`sess_c2a81580a810` to a green check:
> `dataflow OK: verified 4 fact(s) against tool outputs`

The generalisable lesson: an LLM trained on plausible numbers is
exactly as likely to write 540 as 356. Bolting on a dataflow check
that compares the rendered output's primitive facts to the actual
tool outputs catches the entire class of "the model made up a
reasonable-looking number" failure — without needing to model what
"reasonable" means.

### Citation

- `sessions/examples/ex5-edinburgh-research/sess_c2a81580a810/workspace/flyer.html`
- `sessions/examples/ex5-edinburgh-research/sess_c2a81580a810/logs/trace.jsonl`
- `starter/edinburgh_research/integrity.py` — `verify_dataflow`,
  `fact_appears_in_log`

---

## Q3 — Production failure & primitive that surfaces it

### Your answer

**Failure mode**: Loop spiral on `venue_search`. Qwen3-32B (the cohort's
executor model) repeatedly invokes the same tool with mildly varied
arguments (`party_size: 6 → 7 → 5`, `budget: 800 → 1200 → 600`) when
the first result doesn't match its expectations, instead of recognising
that the fixture has only the seven venues it's already enumerated.
The cohort has documented this exact symptom in
`docs/real-mode-failures.md`; Lucia reported it on May 19 and at
£0.10–£0.20 per spiral run the unit cost is small but it explodes
across thousands of bookings/day in production. The Nebius bill
quietly doubles; conversion rate quietly halves; no user-visible
crash.

**Primitive that surfaces it**: the **ticket state machine**. Every
tool call produces a ticket directory under `logs/tickets/tk_<id>/`
with `manifest.json`, `raw_output.json`, `state.json`, `summary.md`.
Per-tool ticket counts — `grep -l '"operation":"venue_search"'
logs/tickets/*/manifest.json | wc -l` — are a one-line diagnostic.
A healthy session has 1–3 calls per tool. A spiral run has 8–20.
The signal is **independent of LLM internals**: the framework doesn't
care whether Qwen "thinks" it's making progress; it counts what
actually happened. A production monitor reading session manifests
(no LLM judge needed) can alert on `venue_search_count > 5` and
surface every spiral within minutes.

This is the same insight as Ex5's dataflow check, applied one level
up: don't ask the LLM whether it's stuck (it'll say no), measure the
output of its actions and compare. Tickets are commits; spirals are
rebase wars; counting them is grep.

### Citation

- `starter/edinburgh_research/tools.py` — `_spiral_check` (defensive
  in-tool guard I added; threshold > 3 returns cached result with
  "STOP" hint in summary)
- `sessions/examples/ex7-handoff-bridge/sess_7141e7342034/logs/tickets/`
  — five tickets, none repeated → healthy run
- Cohort discussion: `docs/real-mode-failures.md` (referenced in
  README §"Real-mode failures are FEATURES")

### Q3 — alternative phrasing (older slide deck draft)

If the question is read as *"if you could keep only one
sovereign-agent primitive, which would it be?"* — session
directories. Tickets, state machines, IPC atomic rename, even the
two-half split, can all be reconstructed from a session directory
that still has `trace.jsonl` and `logs/tickets/`. The opposite isn't
true: reconstructing a session directory from any one of the others
is archaeology. Session-as-directory is the foundation; everything
else is structure on top of it.
