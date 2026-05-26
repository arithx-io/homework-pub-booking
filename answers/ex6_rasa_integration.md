# Ex6 — Rasa structured half

## Your answer

`RasaStructuredHalf.run()` POSTs the normalised booking message to
Rasa's `/webhooks/rest/webhook` and inspects the response array for a
`custom.action` of `"committed"` or `"rejected"`. The validator
(`starter/rasa_half/validator.py`) normalises five fields per
ASSIGNMENT.md §Ex6 (`canonicalise_venue_id`, `_normalise_date`,
`parse_time_24h`, `parse_party_size`, `parse_currency_gbp`) and
returns a Rasa-shaped envelope:
`{"sender": "homework-<sha1[:8]>", "message": "/confirm_booking",
"metadata": {"booking": {...}}}`.

`ActionValidateBooking` (`rasa_project/actions/actions.py`) enforces
the ASSIGNMENT.md caps — party ≤ 8 (`MAX_PARTY_SIZE_FOR_AUTO_BOOKING`)
and deposit ≤ £300 — and emits a deterministic `BK-<sha1[:8]>`
reference on success. The Rasa flow itself (`rasa_project/data/
flows.yml`) is a single `confirm_booking` flow that branches on the
`validation_error` slot to `utter_booking_rejected` or
`utter_booking_confirmed`.

**Cohort decision on flows.** ASSIGNMENT.md §Ex6 lists three flows
(`confirm_booking`, `resume_from_loop`, `request_research`) but the
`flows.yml` comment explicitly says the latter two were removed
intentionally: `resume_from_loop` would need `collect:` steps with
user-facing utter_ask responses (no user types in this scenario),
and `request_research` is better handled at the `HandoffBridge`
level in Python (Ex7). The cohort's Friday sync agreed to follow the
`flows.yml` comment — implement only `confirm_booking`. Ex7's
round-trip handoff is what makes the architecture-level
`request_research` redundant inside Rasa.

**Mock-mode sanity.** I ran `make ex6` (tier 1, stdlib mock Rasa)
end-to-end: party=6, deposit=£200, both under the caps →
`booking confirmed (ref=BK-7D401E9E)`. The mock server emits the
same `custom.action` envelope as real Rasa, so the Python-side
HTTP wiring is identical for both tiers.

## Citations

- `starter/rasa_half/validator.py` — `normalise_booking_payload`
  (5/5 fields normalised), `canonicalise_venue_id`, `parse_time_24h`,
  `parse_currency_gbp`, `parse_party_size`
- `starter/rasa_half/structured_half.py` — `RasaStructuredHalf.run`,
  reference/reason extractors, mock server (`_MockRasaHandler`)
- `rasa_project/actions/actions.py` — `ActionValidateBooking` rule
  checks + reference generation
- `rasa_project/data/flows.yml` — single `confirm_booking` flow, with
  comment explaining why only one flow
