# Ex5 - Edinburgh research loop scenario

## Your answer

In my Ex5 session `sess_eff9faaddd54`, the planner produced two
subgoals both with `assigned_half: "loop"`:

- `sg_1`: "research Edinburgh venues near Haymarket for a party of 6"
- `sg_2`: "produce an HTML flyer with the chosen venue, weather, and cost"

The executor handled `sg_1` in one turn by issuing three tool calls
in parallel: `venue_search`, `get_weather`, `calculate_cost`. All
three are registered with `parallel_safe=True` because they only read
fixtures under `sample_data/`. It then completed `sg_2` with
`generate_flyer` (`parallel_safe=False`, since it writes
`workspace/flyer.html`) and finished with `complete_task`. Ticket
proof: `tk_74097cf1` (planner.plan), `tk_0caa3f69`
(executor.run_subgoal/sg_1), `tk_3e770517` (executor.run_subgoal/sg_2),
all `success`.

Two cohort fixes I applied here:

1. The `calculate_cost` formula in the starter docstring adds
   `min_spend` as a surcharge: `subtotal + service + (hire_fee +
   min_spend)`. That double-charges parties whose subtotal already
   exceeds the minimum spend. I changed it to `max(subtotal,
   min_spend) + service + hire_fee`, treating `min_spend` as a floor
   rather than an additive term (Marat / Dmitry K flagged this in
   Discord). The corrected formula returns `total_gbp=356,
   deposit_required_gbp=71` for the canonical haymarket_tap × party=6
   × 3h × bar_snacks call.

2. `generate_flyer` writes to `_TOOL_CALL_LOG` (the docstring requires
   it), but only with `{"path": "workspace/flyer.html",
   "bytes_written": N}` and a digest of argument *keys*, never the
   rendered fact values. Separately, `verify_dataflow` checks
   producer tool outputs only and ignores `generate_flyer` as a
   renderer. Without both guards a fabricated value could verify
   itself via `generate_flyer`'s own argument log (a circular
   self-validation bug Gareth flagged in Discord). My
   `verify_dataflow` runs clean: `dataflow OK: verified 6 fact(s)
   against tool outputs`.

## Citations

- `sessions/examples/ex5-edinburgh-research/sess_eff9faaddd54/workspace/flyer.html`
- `sessions/examples/ex5-edinburgh-research/sess_eff9faaddd54/logs/trace.jsonl`
  (3 executor.tool_called events, then 1 generate_flyer, then complete_task)
- `sessions/examples/ex5-edinburgh-research/sess_eff9faaddd54/logs/tickets/`
  (three tickets all `success`)
- `starter/edinburgh_research/tools.py` (`_spiral_check` defensive
  guard, `calculate_cost` cohort fix, sanitised `generate_flyer` log args)
- `starter/edinburgh_research/integrity.py` (`verify_dataflow`,
  `_fact_appears_in_producer_output`, `extract_named_entity_facts`)
