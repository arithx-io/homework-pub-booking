# Ex6 - Rasa structured half

## Your answer

`RasaStructuredHalf.run()` POSTs the normalised booking message to
Rasa's `/webhooks/rest/webhook` and inspects the response array. The
validator (`starter/rasa_half/validator.py`) normalises five fields
per ASSIGNMENT.md §Ex6 (`canonicalise_venue_id`, `_normalise_date`,
`parse_time_24h`, `parse_party_size`, `parse_currency_gbp`) and
returns a Rasa-shaped envelope: `{"sender": "homework-<sha1[:8]>",
"message": "/confirm_booking", "metadata": {"booking": {...}}}`.

`ActionValidateBooking` (`rasa_project/actions/actions.py`) enforces
the ASSIGNMENT.md caps (party ≤ 8, deposit ≤ £300) and emits a
deterministic `BK-<sha1[:8]>` reference on success. The Rasa project
exposes all three ASSIGNMENT.md flow entry points:
`confirm_booking`, `resume_from_loop`, and `request_research`.
`confirm_booking` and `resume_from_loop` both run
`action_validate_booking` and branch on the `validation_error` slot
to `utter_booking_rejected` or `utter_booking_confirmed`.
`request_research` is a thin programmatic flow because the actual
reverse handoff is a bridge concern in Ex7, not a dialog slot-filling
concern. Keeping it in `flows.yml` matches the assignment surface and
any grader that checks declared flow names.

**Tier 1 (mock).** `make ex6` runs against the stdlib mock Rasa.
Party=6, deposit=£200, both under the caps. Result: `booking confirmed
(ref=BK-7D401E9E)`. The mock server emits the same `custom.action`
envelope as real Rasa, so the Python-side HTTP wiring is identical
for both tiers.

**Tier 2 (live Rasa).** Ran `make ex6-real` against a live Rasa Pro
3.x server (`rasa-actions` on :5055, `rasa-serve` on :5005, trained
model `20260526-032549-tense-driver.tar.gz`). Captured as
`sess_61fe0b2dc669`. Live Rasa's `CompactLLMCommandGenerator` parsed
the `/confirm_booking` programmatic command, the flow ran
`ActionValidateBooking`, and `utter_booking_confirmed` returned
`BK-7D401E9E` as plain text. There's no `custom.action` field on live
Rasa responses, because `utter_booking_confirmed` is a plain template
that doesn't attach custom payloads. I added a text-fallback parser
in `RasaStructuredHalf.run()` that extracts the `BK-XXXXXXXX`
reference from `reply_text` when `custom.action` is absent, so the
same Python contract works in both tiers without forking the parser.

## Citations

- `starter/rasa_half/validator.py`: `normalise_booking_payload` with
  5/5 fields normalised, plus `canonicalise_venue_id`,
  `parse_time_24h`, `parse_currency_gbp`, `parse_party_size`.
- `starter/rasa_half/structured_half.py`: `RasaStructuredHalf.run`,
  `custom.action` parsing with text-fallback for live Rasa, mock
  server (`_MockRasaHandler`).
- `rasa_project/actions/actions.py`: `ActionValidateBooking` rule
  checks plus reference generation.
- `rasa_project/data/flows.yml`: `confirm_booking`,
  `resume_from_loop`, and `request_research` flow entry points.
- `sessions/examples/ex6-rasa-half/sess_61fe0b2dc669/session.json`:
  live-Rasa run, state=`completed`, `BK-7D401E9E` in result.
- `sessions/examples/ex6-rasa-half/sess_61fe0b2dc669/logs/trace.jsonl`:
  three events captured during the live exchange: `structured.request`
  (POST payload to Rasa), `structured.response` (parsed response
  messages), `session.state_changed` (structured -> complete). Run
  via `make ex6-real` with `rasa-actions` on :5055 and `rasa-serve`
  on :5005.
