"""Generate persistent Ex5 + Ex7 sessions in ./sessions/ for Ex9 to cite.

This script runs the same trajectories as `make ex5` / `make ex7` but writes
the sessions to the repo-local `./sessions/` directory (via
SOVEREIGN_AGENT_DATA_DIR) instead of a tempdir, so the LLM judge can
cross-check Ex9 claims against the committed trace artifacts.

Usage:
    uv run python scripts/generate_ex9_sessions.py
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Persist sessions to ./sessions/ed-research/ and ./sessions/handoff-bridge/
os.environ["SOVEREIGN_AGENT_DATA_DIR"] = str(REPO_ROOT / "sessions")

from sovereign_agent._internal.llm_client import (  # noqa: E402
    FakeLLMClient,
    ScriptedResponse,
    ToolCall,
)
from sovereign_agent._internal.paths import example_sessions_dir  # noqa: E402
from sovereign_agent.executor import DefaultExecutor  # noqa: E402
from sovereign_agent.halves.loop import LoopHalf  # noqa: E402
from sovereign_agent.planner import DefaultPlanner  # noqa: E402
from sovereign_agent.session.directory import create_session  # noqa: E402

from starter.edinburgh_research.integrity import clear_log, verify_dataflow  # noqa: E402
from starter.edinburgh_research.tools import build_tool_registry  # noqa: E402
from starter.handoff_bridge.bridge import HandoffBridge  # noqa: E402
from starter.handoff_bridge.run import _build_fake_client_two_rounds  # noqa: E402
from starter.rasa_half.structured_half import RasaStructuredHalf, spawn_mock_rasa  # noqa: E402


def _build_ex5_fake_client() -> FakeLLMClient:
    """Mirror starter.edinburgh_research.run._build_fake_client but importable."""
    plan_json = json.dumps(
        [
            {
                "id": "sg_1",
                "description": "research Edinburgh venues near Haymarket for a party of 6",
                "success_criterion": "at least one candidate identified",
                "estimated_tool_calls": 3,
                "depends_on": [],
                "assigned_half": "loop",
            },
            {
                "id": "sg_2",
                "description": "produce an HTML flyer with the chosen venue, weather, and cost",
                "success_criterion": "flyer.html written to workspace/",
                "estimated_tool_calls": 1,
                "depends_on": ["sg_1"],
                "assigned_half": "loop",
            },
        ]
    )
    return FakeLLMClient(
        [
            ScriptedResponse(content=plan_json),
            ScriptedResponse(
                tool_calls=[
                    ToolCall(
                        id="c1",
                        name="venue_search",
                        arguments={"near": "Haymarket", "party_size": 6, "budget_max_gbp": 800},
                    ),
                    ToolCall(
                        id="c2",
                        name="get_weather",
                        arguments={"city": "edinburgh", "date": "2026-04-25"},
                    ),
                    ToolCall(
                        id="c3",
                        name="calculate_cost",
                        arguments={
                            "venue_id": "haymarket_tap",
                            "party_size": 6,
                            "duration_hours": 3,
                            "catering_tier": "bar_snacks",
                        },
                    ),
                ]
            ),
            ScriptedResponse(
                tool_calls=[
                    ToolCall(
                        id="c4",
                        name="generate_flyer",
                        arguments={
                            "event_details": {
                                "venue_name": "Haymarket Tap",
                                "venue_address": "12 Dalry Rd, Edinburgh EH11 2BG",
                                "date": "2026-04-25",
                                "time": "19:30",
                                "party_size": 6,
                                "condition": "cloudy",
                                "temperature_c": 12,
                                "total_gbp": 356,
                                "deposit_required_gbp": 71,
                            }
                        },
                    )
                ]
            ),
            ScriptedResponse(
                tool_calls=[
                    ToolCall(
                        id="c5",
                        name="complete_task",
                        arguments={
                            "result": {
                                "flyer": "workspace/flyer.html",
                                "venue": "haymarket_tap",
                            }
                        },
                    )
                ]
            ),
            ScriptedResponse(content="Subgoal 1 complete."),
            ScriptedResponse(content="Booking researched; flyer at workspace/flyer.html."),
            ScriptedResponse(content="Task complete."),
        ]
    )


async def make_ex5_session() -> str:
    """Run the Ex5 scripted scenario and persist artifacts."""
    clear_log()
    with example_sessions_dir("ex5-edinburgh-research", persist=True) as sessions_root:
        session = create_session(
            scenario="edinburgh-research",
            task=(
                "Research an Edinburgh pub and produce an HTML event flyer.\n\n"
                "Context: party=6, date=2026-04-25, time=19:30, near Haymarket."
            ),
            sessions_dir=sessions_root,
        )
        client = _build_ex5_fake_client()
        tools = build_tool_registry(session)
        half = LoopHalf(
            planner=DefaultPlanner(model="fake", client=client),
            executor=DefaultExecutor(model="fake", client=client, tools=tools),
        )
        result = await half.run(session, {"task": "research Edinburgh venue and write flyer"})

        flyer_path = session.workspace_dir / "flyer.html"
        flyer_content = flyer_path.read_text(encoding="utf-8") if flyer_path.exists() else ""
        integrity = verify_dataflow(flyer_content)

        print(f"  ex5 session: {session.directory}")
        print(f"    loop outcome: {result.next_action}")
        print(f"    dataflow:     {integrity.summary}")
        return session.session_id


async def make_ex7_session() -> str:
    """Run the Ex7 two-round bridge against the mock Rasa server, persisted."""
    server, _thread, mock_url = spawn_mock_rasa(port=5907)
    try:
        with example_sessions_dir("ex7-handoff-bridge", persist=True) as sessions_root:
            session = create_session(
                scenario="ex7-handoff-bridge",
                task="Book a venue for 12 people in Haymarket, Friday 19:30.",
                sessions_dir=sessions_root,
            )
            client = _build_fake_client_two_rounds()
            tools = build_tool_registry(session)
            loop_half = LoopHalf(
                planner=DefaultPlanner(model="fake", client=client),
                executor=DefaultExecutor(model="fake", client=client, tools=tools),
            )
            bridge = HandoffBridge(
                loop_half=loop_half,
                structured_half=RasaStructuredHalf(rasa_url=mock_url),
                max_rounds=3,
            )
            result = await bridge.run(session, {"task": "book for party of 12 in Haymarket"})
            print(f"  ex7 session: {session.directory}")
            print(f"    outcome:    {result.outcome}")
            print(f"    rounds:     {result.rounds}")
            print(f"    summary:    {result.summary}")
            return session.session_id
    finally:
        server.shutdown()


async def main() -> None:
    print("Generating persistent sessions for Ex9 to cite...")
    print()
    ex5_id = await make_ex5_session()
    print()
    ex7_id = await make_ex7_session()
    print()
    print("Done. Citable IDs:")
    print(f"  Ex5: {ex5_id}")
    print(f"  Ex7: {ex7_id}")


if __name__ == "__main__":
    asyncio.run(main())
