# Grading rubric — student-facing overview

This is a plain-English version of `grader/rubric.py`. If they ever
disagree, `grader/rubric.py` is authoritative — open an issue so we can
fix this doc.

## The three layers

| Layer | Points | What it checks | Runs where |
|---|---|---|---|
| Mechanical | 30 | Does your code compile, lint, and import cleanly? Are all answer files present and non-empty? | Locally + CI |
| Behavioural | 40 | Does your code actually work — end-to-end scenario runs, dataflow checks catch fabrications, handoffs round-trip? | Partial locally, full in CI |
| Reasoning | 30 | Are your Ex9 answers grounded in real logs, specific, and the right length? | CI only (LLM judge) |

## Mechanical layer breakdown (30 pts)

| Check | Points | How to pass |
|---|---|---|
| Required files present | 2 | Keep `README.md`, `ASSIGNMENT.md`, `pyproject.toml`, `Makefile`, `SETUP.md`. Don't rename them. |
| `sovereign-agent == 0.2.0` pin | 2 | Don't edit `pyproject.toml`'s dependency line unless a CHANGELOG entry tells you to. |
| `make setup` succeeds | 3 | Standard — should just work after cloning. |
| `make lint` clean | 3 | Ruff errors. Fix with `make format` + manual pass. |
| `make format-check` clean | 2 | Run `make format` before committing. |
| `pytest --collect-only` succeeds | 3 | No import errors, no syntax errors. |
| All public tests pass | 5 | `make test` green. |
| All 5 answer files exist | 2 | Don't delete templates. |
| Answer files not empty | 3 | Replace every "*(Write your answer below this line)*" placeholder. |
| Every scenario has a dataflow check | 5 | `verify_dataflow` (or equivalent) in Ex5 and Ex7. **−10 pt penalty if missing.** |

## Behavioural layer breakdown (40 pts)

| Check | Points |
|---|---|
| Ex5 runs end-to-end, flyer.md written | 6 |
| Ex5 dataflow catches planted fabrication (grader injects £9999, castle, etc.) | 6 |
| Ex5 dataflow does NOT false-positive on legit flyer | 3 |
| Ex6 structured half accepts valid booking | 4 |
| Ex6 rejects oversize party | 3 |
| Ex6 rejects high deposit | 3 |
| Ex7 round-trip completes (reject → re-research → approve) | 6 |
| Ex7 never has >1 handoff file visible at once | 2 |
| Ex8 text mode at least 3 turns | 4 |
| Ex8 trace has voice.utterance_in and _out events | 3 |

## Reasoning layer breakdown (30 pts)

Scored by an LLM-as-judge that reads your Ex9 answers AND your session
artifacts (trace, tickets). Uses a model DIFFERENT from the one you used
(so the judge can't just confirm what the same model wrote).

| Check | Points |
|---|---|
| Q1 grounded in real Ex7 logs with specific subgoal cited | 9 |
| Q2 describes a specific, reproducible integrity-check scenario | 9 |
| Q3 names EXACTLY ONE primitive and ONE failure mode | 6 |
| All answers within word-count bounds (100-400) | 3 |
| Judge gives ≥0.5 on groundedness | 3 |

## Penalties (applied AFTER summing)

- **−10 pts**: any scenario lacks a dataflow integrity check. See
  `grader/integrity_check.py` for the exact detection rule.
- **Zero on affected exercise**: committing a secret (real API key, etc.).
  Caught automatically by grader.

## Bonus

- **+4 pts** on Ex8: real voice mode end-to-end with working STT.
  Not required for full credit on Ex8 via text mode alone.

## What "local" vs "CI" means for your score

`make check-submit` runs locally and reproduces:
- Full Mechanical layer
- Partial Behavioural (public tests, but not the dataflow probe or Ex7 full round-trip)
- No Reasoning (can't run the LLM judge locally)

Typical local-to-CI mapping:

| Local | CI (typical) | Meaning |
|---|---|---|
| 65-70 | 90-95 | Everything working well |
| 50-60 | 70-80 | A few things broken but solid foundation |
| <40 | <50 | Major issues — run `make verify` and `docs/troubleshooting.md` |

A CI score lower than expected from your local run means you broke
something in the private tests. Check the CI report's "Behavioural" section
for which specific check failed.

## Regrading

If you believe a judgment is wrong, open an issue with the `regrade`
label and cite:

- The specific rubric check name (from `grader/rubric.py`).
- The evidence in your repo (file path and line numbers).
- Why you think the check should have passed.

We regrade manually within 3 business days.
