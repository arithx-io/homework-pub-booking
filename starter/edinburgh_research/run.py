"""Ex5 — Edinburgh research scenario entrypoint.

Usage:
    make ex5            # offline, FakeLLMClient
    make ex5-real       # uses Nebius (burns tokens)

The structure mirrors examples/pub_booking/run.py in the sovereign-agent
repo. If you're unsure how to wire something up, read that file — the
pedagogical model is "copy from the reference, change the scenario".
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from sovereign_agent._internal.llm_client import (
    FakeLLMClient,
    OpenAICompatibleClient,
    ScriptedResponse,
    ToolCall,
)
from sovereign_agent._internal.paths import user_data_dir
from sovereign_agent.executor import DefaultExecutor
from sovereign_agent.halves.loop import LoopHalf
from sovereign_agent.planner import DefaultPlanner
from sovereign_agent.session.directory import create_session
from sovereign_agent.tickets.ticket import list_tickets

from starter.edinburgh_research.integrity import clear_log, verify_dataflow
from starter.edinburgh_research.tools import build_tool_registry


# ---------------------------------------------------------------------------
# Scripted trajectory for offline mode
# ---------------------------------------------------------------------------
def _build_fake_client() -> FakeLLMClient:
    """Scripts a realistic 2-subgoal trajectory for the FakeLLMClient.

    You MAY modify this to exercise different paths through your code,
    but keep at least one tool call for each of the four tools so the
    integrity check has data to verify.
    """
    plan_json = json.dumps(
        [
            {
                "id": "sg_1",
                "description": "research Edinburgh venues near Haymarket for a party of 6",
                "success_criterion": "at least one candidate venue identified with cost estimate",
                "estimated_tool_calls": 3,
                "depends_on": [],
                "assigned_half": "loop",
            },
            {
                "id": "sg_2",
                "description": "produce a flyer with the chosen venue, weather, and cost",
                "success_criterion": "flyer.md written to workspace/",
                "estimated_tool_calls": 1,
                "depends_on": ["sg_1"],
                "assigned_half": "loop",
            },
        ]
    )

    # sg_1: three parallel_safe reads
    search_call = ToolCall(
        id="c1",
        name="venue_search",
        arguments={"near": "Haymarket", "party_size": 6, "budget_max_gbp": 800},
    )
    weather_call = ToolCall(
        id="c2",
        name="get_weather",
        arguments={"city": "edinburgh", "date": "2026-04-25"},
    )
    cost_call = ToolCall(
        id="c3",
        name="calculate_cost",
        arguments={
            "venue_id": "haymarket_tap",
            "party_size": 6,
            "duration_hours": 3,
            "catering_tier": "bar_snacks",
        },
    )
    # sg_2: flyer write + complete
    flyer_call = ToolCall(
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
                "total_gbp": 540,
                "deposit_required_gbp": 0,
            }
        },
    )
    complete_call = ToolCall(
        id="c5",
        name="complete_task",
        arguments={"result": {"flyer": "workspace/flyer.md", "venue": "haymarket_tap"}},
    )

    return FakeLLMClient(
        [
            # Planner response
            ScriptedResponse(content=plan_json),
            # Executor turn 1 — three reads in parallel
            ScriptedResponse(tool_calls=[search_call, weather_call, cost_call]),
            # Executor turn 2 — flyer write (sequential, parallel_safe=False)
            ScriptedResponse(tool_calls=[flyer_call]),
            # Executor turn 3 — complete
            ScriptedResponse(tool_calls=[complete_call]),
            # Final text
            ScriptedResponse(content="Booking researched; flyer at workspace/flyer.md."),
        ]
    )


# ---------------------------------------------------------------------------
# Session directory routing
# ---------------------------------------------------------------------------
def _sessions_root(real: bool) -> Path:
    """Where to write session artifacts.

    Offline: under user_data_dir()/homework/ex5 so students can inspect
    the session afterwards without polluting their cwd.

    --real: same convention. Real-LLM runs are expensive; keep the
    artifacts.
    """
    root = user_data_dir() / "homework" / "ex5"
    root.mkdir(parents=True, exist_ok=True)
    return root


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------
async def run_scenario(real: bool) -> int:
    clear_log()

    sessions_root = _sessions_root(real)
    session = create_session(
        scenario="edinburgh-research",
        task=(
            "Find an Edinburgh pub near Haymarket for a party of 6 on "
            "2026-04-25 at 19:30. Check the weather, work out the catering "
            "cost, and write a flyer to workspace/flyer.md."
        ),
        sessions_dir=sessions_root,
    )
    print(f"Session {session.session_id}")
    print(f"  dir: {session.directory}")

    if real:
        print("  LLM: Nebius Token Factory (live)")
        client = OpenAICompatibleClient(
            base_url="https://api.tokenfactory.nebius.com/v1/",
            api_key_env="NEBIUS_KEY",
        )
        planner_model = "Qwen/Qwen3-Next-80B-A3B-Thinking"
        executor_model = "Qwen/Qwen3-32B"
    else:
        print("  LLM: FakeLLMClient (offline, scripted)")
        client = _build_fake_client()
        planner_model = executor_model = "fake"

    tools = build_tool_registry(session)
    half = LoopHalf(
        planner=DefaultPlanner(model=planner_model, client=client),
        executor=DefaultExecutor(model=executor_model, client=client, tools=tools),  # type: ignore[arg-type]
    )

    result = await half.run(session, {"task": "research Edinburgh venue and write flyer"})
    print(f"\nLoop half outcome: {result.next_action}")
    print(f"  summary: {result.summary}")

    # Tickets summary
    print("\nTickets:")
    for t in list_tickets(session):
        r = t.read_result()
        print(f"  {t.ticket_id}  {t.operation:50s}  {r.state.value}")

    # Integrity check — read the flyer back and verify.
    flyer_path = session.workspace_dir / "flyer.md"
    if not flyer_path.exists():
        print("\n✗ No flyer written to workspace/. Ex5 failed.")
        return 1

    print(f"\n=== flyer.md ({flyer_path.stat().st_size} bytes) ===")
    flyer_content = flyer_path.read_text(encoding="utf-8")
    print(flyer_content[:500] + ("...\n[truncated]" if len(flyer_content) > 500 else ""))

    # Dataflow check — this is the part of Ex5 the grader scores most heavily.
    print("\n=== Dataflow integrity check ===")
    integrity = verify_dataflow(flyer_content)
    if integrity.ok:
        print(f"✓  {integrity.summary}")
        if integrity.verified_facts:
            print(f"   Verified {len(integrity.verified_facts)} fact(s) against tool outputs.")
    else:
        print(f"✗  {integrity.summary}")
        print(f"   Unverified facts: {integrity.unverified_facts}")
        print(
            "\n   Either (a) a tool returned data that never reached the flyer, "
            "(b) the LLM fabricated a value, or (c) your verify_dataflow is "
            "too strict. Investigate which."
        )
        return 2

    return 0


def main() -> None:
    real = "--real" in sys.argv
    exit_code = asyncio.run(run_scenario(real=real))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
