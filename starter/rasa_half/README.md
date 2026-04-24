# Ex6 — Rasa structured half

**You are building:** a `StructuredHalf` subclass that uses Rasa CALM as its
dialog manager, with a custom validation action that enforces deposit and
party-size caps.

**Spec:** see `ASSIGNMENT.md` §Ex6.

**Time estimate:** 3-5 hours (most of it is Rasa setup on first use).

## Prerequisites

- Docker installed (see `docs/rasa-docker.md`).
- Finished Ex5 — you'll reuse concepts.

## Files in this directory

| File | What it is | Your job |
|---|---|---|
| `structured_half.py` | `RasaStructuredHalf` subclass | Implement the HTTP bridge to the Rasa container |
| `validator.py` | Booking-data normaliser | Convert raw dicts to Rasa-ready payloads |
| `run.py` | Scenario runner | Wire it together; offline mode uses a mock Rasa server |

Plus the Rasa project itself under `../../rasa_project/`:

- `data/flows.yml` — three flows to implement
- `actions/actions.py` — `ActionValidateBooking` custom action

## How to run

```
# Offline mode (mock Rasa server, zero network)
make ex6

# Real mode (live Rasa container)
make ex6-real
```

## Key design points

- Your `StructuredHalf` subclass speaks HTTP to `http://localhost:5005/webhooks/rest/webhook`.
- The custom action server runs on `http://localhost:5055/webhook`.
- Validation rules (from sample_data/catering.json):
  - deposit_required_gbp > £300 → reject with reason
  - party_size > 8 → reject with reason
  - Both pass → return `action: committed` with a booking reference
