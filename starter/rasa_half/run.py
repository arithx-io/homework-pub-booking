"""Ex6 — runner for the Rasa structured half.

Offline mode uses a mock Rasa server (stdlib http.server in a thread) so
the test suite runs without Docker. --real requires a running Rasa
container on localhost:5005.
"""

from __future__ import annotations

import asyncio
import sys

from sovereign_agent._internal.paths import user_data_dir
from sovereign_agent.session.directory import create_session

from starter.rasa_half.structured_half import RasaStructuredHalf


async def run_scenario(real: bool) -> int:
    sessions_root = user_data_dir() / "homework" / "ex6"
    sessions_root.mkdir(parents=True, exist_ok=True)

    session = create_session(
        scenario="ex6-rasa",
        task="Confirm a booking through the Rasa structured half.",
        sessions_dir=sessions_root,
    )
    print(f"Session {session.session_id}")

    if real:
        print("  Rasa URL: http://localhost:5005/webhooks/rest/webhook")
        half = RasaStructuredHalf()
    else:
        print("  Using mock Rasa server on localhost (auto-spawned).")
        # TODO (optional): spin up a stdlib http.server that responds with
        # a scripted list of Rasa-shaped messages. See docs/rasa-docker.md
        # for the expected response shape.
        half = RasaStructuredHalf(rasa_url="http://localhost:5905/webhooks/rest/webhook")

    sample_booking = {
        "data": {
            "action": "confirm_booking",
            "venue_id": "Haymarket Tap",
            "date": "25th April 2026",
            "time": "7:30pm",
            "party_size": "6",
            "deposit": "£200",
        }
    }

    result = await half.run(session, sample_booking)
    print(f"\nStructured half outcome: {result.next_action}")
    print(f"  summary: {result.summary}")
    print(f"  output: {result.output}")
    return 0 if result.success else 1


def main() -> None:
    real = "--real" in sys.argv
    sys.exit(asyncio.run(run_scenario(real=real)))


if __name__ == "__main__":
    main()
