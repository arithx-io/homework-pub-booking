"""Custom Rasa actions for the homework.

This file runs inside the Rasa action server (`make rasa-actions`).
It imports from rasa_sdk which is only available in that environment —
don't try to run this file from your homework venv.

Your task: implement ActionValidateBooking.

IMPORTANT — how the booking data reaches the action:

  Your RasaStructuredHalf POSTs to Rasa's REST webhook with this shape:
    {"sender": ..., "message": "/confirm_booking",
     "metadata": {"booking": {"venue_id": ..., "party_size": 6, ...}}}

  CALM's LLM command generator turns "/confirm_booking" into a
  StartFlow(confirm_booking) command. But it does NOT automatically
  read metadata into slots — that's your action's job.

  Inside `run()`, read metadata like this:
    latest = tracker.latest_message or {}
    meta = latest.get("metadata") or {}
    booking = meta.get("booking") or {}
    venue_id = booking.get("venue_id")
    ...

  Then SlotSet each value (so the responses can interpolate them)
  AND emit a validation_error SlotSet with either a reason or None.
"""

from __future__ import annotations

from typing import Any

# rasa_sdk is provided by the Rasa container, not the homework venv.
# Your IDE may complain about these imports outside the container.
# `SlotSet` is marked noqa: F401 — you'll use it when you implement
# ActionValidateBooking.run().
from rasa_sdk import Action, Tracker  # type: ignore[import-not-found]
from rasa_sdk.events import SlotSet  # type: ignore[import-not-found]  # noqa: F401
from rasa_sdk.executor import CollectingDispatcher  # type: ignore[import-not-found]

# Rules — see ASSIGNMENT.md §Ex6 and sample_data/catering.json.
MAX_PARTY_SIZE_FOR_AUTO_BOOKING = 8
MAX_DEPOSIT_FOR_AUTO_BOOKING_GBP = 300


class ActionValidateBooking(Action):
    """Validate the proposed booking. Returns one of:

    * Success: SlotSet("validation_error", None), plus a booking_reference.
    * Rejection: SlotSet("validation_error", "<reason>").

    The reason string is propagated to the user AND back to
    RasaStructuredHalf via the response message.

    Rules:
      * party_size > 8         → reject with "party_too_large"
      * deposit_gbp > 300      → reject with "deposit_too_high"
      * missing required field → reject with "missing_<field>"
      * otherwise              → success
    """

    def name(self) -> str:
        return "action_validate_booking"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: dict[str, Any],
    ) -> list[dict[str, Any]]:
        # Step 1: read booking data from metadata.
        #    latest = tracker.latest_message or {}
        #    meta = latest.get("metadata") or {}
        #    booking = meta.get("booking") or {}
        #
        # Step 2: pull each field (venue_id, date, time, party_size, deposit_gbp).
        #
        # Step 3: SlotSet each field so downstream responses can interpolate them
        # (e.g. "{party_size}", "{booking_reference}").
        #
        # Step 4: check the rules in order. Return early with the appropriate
        # SlotSet("validation_error", "<reason>") when a rule fires.
        #
        # Step 5: if all rules pass, compute a booking reference and return
        # SlotSet("validation_error", None) + SlotSet("booking_reference", ...).
        #
        # Happy-path reference format:
        #   import hashlib
        #   ref = "BK-" + hashlib.sha1(
        #       f"{venue_id}|{date}|{time}|{party_size}".encode()
        #   ).hexdigest()[:8].upper()

        raise NotImplementedError(
            "TODO Ex6: implement ActionValidateBooking.run — see this file's "
            "docstring and ASSIGNMENT.md §Ex6 for the rules."
        )
