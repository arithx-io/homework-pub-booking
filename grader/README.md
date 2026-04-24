# grader/

**Not the authoritative grader.** The authoritative run happens in CI at the
submission deadline via `.github/workflows/grade.yml`, which additionally
materialises the private tests from a separate grader repo. This local grader
reproduces about 70% of the CI run — enough for a fast feedback loop.

## Layers

| Layer | Points | What's checked | Local? |
|---|---|---|---|
| **Mechanical** | 30 | `make ci` green, answers populated, scaffolds compile | ✓ |
| **Behavioural** | 40 | End-to-end runs, dataflow probe, voice trace correctness | Partial (public only) |
| **Reasoning** | 30 | Q1-Q3 grounded in YOUR logs, specific ticket IDs | ✗ (needs LLM judge) |

Local `make check-submit` scores the Mechanical layer fully, a subset of
Behavioural, and does NOT score Reasoning (that needs an LLM judge). Expect
a local score in the 60-75 range when you're passing; CI adds the rest.

## Penalty

−10 pts from Mechanical if any scenario ships without a dataflow integrity
check. **Every scenario must have one.** No exceptions.

## Planted failures

The CI grader edits one of your tool outputs before running Ex5 to inject
a fabricated value. A correctly-implemented dataflow check catches this.
If the check passes through the plant → your dataflow check is too lenient.

## Running manually

```
# Full local run:
make check-submit

# Just one exercise:
python -m grader.check_submit --only ex5

# Verbose, show each check's reasoning:
python -m grader.check_submit --verbose
```
