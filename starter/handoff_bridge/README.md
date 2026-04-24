# Ex7 — Handoff bridge

**You are building:** the glue that routes handoffs back and forth between
the loop half (Ex5) and the structured half (Ex6), achieving a bidirectional
round-trip.

**Spec:** see `ASSIGNMENT.md` §Ex7.

**Time estimate:** 2-3 hours.

## Prerequisites

- Ex5 complete and `make ex5` green.
- Ex6 complete and `make ex6` green.

## Files

| File | What it is | Your job |
|---|---|---|
| `bridge.py` | Bridge logic | Implement the routing between halves |
| `run.py` | End-to-end demo | Drives the scenario; assert the round-trip happens |

## How to run

```
make ex7
```

## The trajectory you must achieve

1. Task: "party of 12, Haymarket, Friday 19:30".
2. Loop half researches, finds `haymarket_tap` (8 seats — won't fit 12).
3. Loop hands off to structured half with venue_id=haymarket_tap.
4. Structured half REJECTS (party > 8 cap).
5. Bridge catches the reject, hands BACK to loop with "try a bigger venue".
6. Loop researches again, finds `royal_oak` (16 seats).
7. Loop hands off to structured half with venue_id=royal_oak.
8. Structured half APPROVES.
9. Session marks complete.

At most ONE `handoff_to_*.json` file should be visible in `ipc/` at any
time. Multiple simultaneous handoffs violate the sovereign-agent contract
and will be flagged by `IpcWatcher` as `SA_IO_MALFORMED_HANDOFF_STATE`.

## Key invariants

- Forward handoffs carry the FULL prior context (subgoal results, constraints).
- Reverse handoffs carry the REJECTION REASON as context so the loop half
  can adapt its next plan.
- The session trace should show clear `session.state_changed` events for
  each transition.
