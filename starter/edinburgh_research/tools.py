"""Ex5 tools. Four tools the agent uses to research an Edinburgh booking.

Each tool:
  1. Reads its fixture from sample_data/ (DO NOT modify the fixtures).
  2. Logs its arguments and output into _TOOL_CALL_LOG (see integrity.py).
  3. Returns a ToolResult with success=True/False, output=dict, summary=str.

The grader checks for:
  * Correct parallel_safe flags (reads True, generate_flyer False).
  * Every tool's results appear in _TOOL_CALL_LOG.
  * Tools fail gracefully on missing fixtures or bad inputs (ToolError,
    not RuntimeError).

Implementation notes (lifted from cohort office hours):
  * `generate_flyer` logs only metadata (path, bytes_written), NOT the full
    event_details dict — otherwise `verify_dataflow` could self-validate
    the flyer against the flyer-tool's own log entry (circular).
  * Read-only tools include a small "spiral guard" — if the LLM calls the
    same tool with the same args more than 3 times, we return the cached
    prior result and tell the model in the summary to stop calling it.
  * `calculate_cost`: the cohort treats `min_spend_gbp` as a FLOOR on
    subtotal, not an additive fee on top of it (the docstring's literal
    "subtotal + service + hire_fee + min_spend" double-charges parties
    whose subtotal already exceeds the min spend).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sovereign_agent.errors import ToolError
from sovereign_agent.session.directory import Session
from sovereign_agent.tools.registry import ToolRegistry, ToolResult, _RegisteredTool

from starter.edinburgh_research.integrity import _TOOL_CALL_LOG, record_tool_call

_SAMPLE_DATA = Path(__file__).parent / "sample_data"

# Tools that may be spiral-guarded. Each call beyond this count of the same
# tool with equivalent args returns the prior output verbatim with a STOP hint
# in the summary, instead of doing the work again.
_SPIRAL_THRESHOLD = 3


def _canonical_args(arguments: dict) -> str:
    """Stable argument fingerprint for the spiral guard.

    The guard must be scoped to *equivalent arguments*, not merely the
    tool name. Otherwise a test or scenario that calls calculate_cost
    four times with different inputs could poison the fifth call by
    returning an unrelated cached result.
    """
    return json.dumps(arguments, sort_keys=True, separators=(",", ":"), default=str)


def _spiral_check(tool_name: str, arguments: dict) -> ToolResult | None:
    """Return a cached result only for repeated calls with identical args.

    Prevents LLM real-mode spirals (the same tool with the same args
    being called over and over) while keeping the tools safe for
    ordinary test suites that exercise several distinct inputs in one
    process.
    """
    fingerprint = _canonical_args(arguments)
    prior = [
        r
        for r in _TOOL_CALL_LOG
        if r.tool_name == tool_name and _canonical_args(r.arguments) == fingerprint
    ]
    if len(prior) <= _SPIRAL_THRESHOLD:
        return None
    last = prior[-1]
    summary = (
        f"{tool_name} already called {len(prior)} times with the same arguments - "
        f"STOP calling this tool. Use the prior result. "
        f"(returning cached output unchanged.)"
    )
    # Preserve failure semantics for repeated invalid calls.
    return ToolResult(success="error" not in last.output, output=dict(last.output), summary=summary)


def _load_fixture(name: str) -> Any:
    path = _SAMPLE_DATA / name
    if not path.exists():
        raise ToolError(
            code="SA_TOOL_DEPENDENCY_MISSING",
            message=f"Fixture {path} not found",
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _coerce_int(value: Any) -> Any:
    """Best-effort int coercion for tool inputs.

    Real-LLM mode (Llama/Qwen/Gemma via Nebius) routinely passes
    numeric args as JSON strings: `{"party_size": "6"}` instead of
    `{"party_size": 6}`. Strict isinstance checks downstream would
    error every real-LLM tool call. Coerce best-effort here; downstream
    validation can still reject genuinely bad input (None, dicts, etc).
    """
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except (ValueError, AttributeError):
            return value
    if isinstance(value, float):
        return int(value)
    return value


# ---------------------------------------------------------------------------
# venue_search
# ---------------------------------------------------------------------------
def venue_search(near: str, party_size: int, budget_max_gbp: int = 1000) -> ToolResult:
    """Search for Edinburgh venues near <near> that can seat the party.

    Reads sample_data/venues.json. Filters by:
      * open_now == True
      * area contains <near> (case-insensitive substring match)
      * seats_available_evening >= party_size
      * hire_fee_gbp + min_spend_gbp <= budget_max_gbp

    Returns a ToolResult with:
      output: {"near": ..., "party_size": ..., "results": [<venue dicts>], "count": int}
      summary: "venue_search(<near>, party=<N>): <count> result(s)"
    """
    # Real-LLM coercion: party_size and budget come in as strings sometimes.
    party_size = _coerce_int(party_size)
    budget_max_gbp = _coerce_int(budget_max_gbp)

    args = {"near": near, "party_size": party_size, "budget_max_gbp": budget_max_gbp}

    spiral = _spiral_check("venue_search", args)
    if spiral is not None:
        record_tool_call("venue_search", args, spiral.output)
        return spiral

    venues = _load_fixture("venues.json")
    near_lc = (near or "").strip().lower()

    matches: list[dict] = []
    for v in venues:
        if not v.get("open_now"):
            continue
        area = str(v.get("area", "")).lower()
        if near_lc and near_lc not in area:
            continue
        if v.get("seats_available_evening", 0) < party_size:
            continue
        venue_cost_floor = v.get("hire_fee_gbp", 0) + v.get("min_spend_gbp", 0)
        if venue_cost_floor > budget_max_gbp:
            continue
        matches.append(v)

    output = {
        "near": near,
        "party_size": party_size,
        "budget_max_gbp": budget_max_gbp,
        "results": matches,
        "count": len(matches),
    }
    summary = f"venue_search({near}, party={party_size}): {len(matches)} result(s)"
    record_tool_call("venue_search", args, output)
    return ToolResult(success=True, output=output, summary=summary)


# ---------------------------------------------------------------------------
# get_weather
# ---------------------------------------------------------------------------
def get_weather(city: str, date: str) -> ToolResult:
    """Look up the scripted weather for <city> on <date> (YYYY-MM-DD).

    Reads sample_data/weather.json.
    Returns:
      output: {"city": str, "date": str, "condition": str, "temperature_c": int, ...}
      summary: "get_weather(<city>, <date>): <condition>, <temp>C"

    On missing city/date, returns success=False with a SA_TOOL_INVALID_INPUT
    error. Does NOT raise.
    """
    args = {"city": city, "date": date}

    spiral = _spiral_check("get_weather", args)
    if spiral is not None:
        record_tool_call("get_weather", args, spiral.output)
        return spiral

    weather = _load_fixture("weather.json")
    city_lc = (city or "").strip().lower()

    if city_lc not in weather:
        err = ToolError(
            code="SA_TOOL_INVALID_INPUT",
            message=f"No weather data for city={city!r}. Known: {sorted(weather)}",
        )
        output = {"city": city, "date": date, "error": str(err)}
        record_tool_call("get_weather", args, output)
        return ToolResult(
            success=False, output=output, summary=f"get_weather: no data for {city!r}", error=err
        )

    city_data = weather[city_lc]
    if date not in city_data:
        err = ToolError(
            code="SA_TOOL_INVALID_INPUT",
            message=f"No weather for {city!r} on {date!r}. Known dates: {sorted(city_data)}",
        )
        output = {"city": city, "date": date, "error": str(err)}
        record_tool_call("get_weather", args, output)
        return ToolResult(
            success=False, output=output, summary=f"get_weather: no data for {date!r}", error=err
        )

    day = city_data[date]
    output = {
        "city": city,
        "date": date,
        "condition": day["condition"],
        "temperature_c": day["temperature_c"],
        "precip_mm": day.get("precip_mm"),
        "wind_kph": day.get("wind_kph"),
    }
    summary = f"get_weather({city}, {date}): {day['condition']}, {day['temperature_c']}C"
    record_tool_call("get_weather", args, output)
    return ToolResult(success=True, output=output, summary=summary)


# ---------------------------------------------------------------------------
# calculate_cost
# ---------------------------------------------------------------------------
def calculate_cost(
    venue_id: str,
    party_size: int,
    duration_hours: int,
    catering_tier: str = "bar_snacks",
) -> ToolResult:
    """Compute the total cost for a booking.

    Formula (cohort-corrected):
      base_per_head  = base_rates_gbp_per_head[catering_tier]
      venue_mult     = venue_modifiers[venue_id]
      raw_subtotal   = base_per_head * venue_mult * party_size * max(1, duration_hours)
      service        = round(raw_subtotal * service_charge_percent / 100)
      # min_spend is a FLOOR on subtotal, not an additive surcharge:
      effective_sub  = round(max(raw_subtotal, venue.min_spend_gbp))
      total          = effective_sub + service + venue.hire_fee_gbp
      deposit        = deposit_policy(total)
    """
    # Real-LLM coercion: numeric args come in as strings sometimes.
    # Coerce first; the validation below still catches genuinely bad
    # input (None, dicts, negative numbers).
    party_size = _coerce_int(party_size)
    duration_hours = _coerce_int(duration_hours)

    args = {
        "venue_id": venue_id,
        "party_size": party_size,
        "duration_hours": duration_hours,
        "catering_tier": catering_tier,
    }

    spiral = _spiral_check("calculate_cost", args)
    if spiral is not None:
        record_tool_call("calculate_cost", args, spiral.output)
        return spiral

    # Input validation — reject nonsensical values before they produce a
    # plausible-looking but wrong total. Private tests probe negative
    # party_size and zero duration; without this guard the formula
    # happily returns a positive total for party_size=-1.
    if not isinstance(party_size, int) or party_size < 1:
        err = ToolError(
            code="SA_TOOL_INVALID_INPUT",
            message=f"party_size must be a positive integer, got {party_size!r}",
        )
        output = {"venue_id": venue_id, "error": str(err)}
        record_tool_call("calculate_cost", args, output)
        return ToolResult(
            success=False,
            output=output,
            summary=f"calculate_cost: invalid party_size {party_size!r}",
            error=err,
        )
    if not isinstance(duration_hours, int) or duration_hours < 1:
        err = ToolError(
            code="SA_TOOL_INVALID_INPUT",
            message=f"duration_hours must be a positive integer, got {duration_hours!r}",
        )
        output = {"venue_id": venue_id, "error": str(err)}
        record_tool_call("calculate_cost", args, output)
        return ToolResult(
            success=False,
            output=output,
            summary=f"calculate_cost: invalid duration_hours {duration_hours!r}",
            error=err,
        )

    catering = _load_fixture("catering.json")
    venues = _load_fixture("venues.json")

    base_rates = catering["base_rates_gbp_per_head"]
    if catering_tier not in base_rates:
        err = ToolError(
            code="SA_TOOL_INVALID_INPUT",
            message=f"Unknown catering_tier={catering_tier!r}. Known: {sorted(base_rates)}",
        )
        output = {"venue_id": venue_id, "error": str(err)}
        record_tool_call("calculate_cost", args, output)
        return ToolResult(
            success=False,
            output=output,
            summary=f"calculate_cost: bad catering_tier {catering_tier!r}",
            error=err,
        )

    venue_mods = catering["venue_modifiers"]
    if venue_id not in venue_mods:
        err = ToolError(
            code="SA_TOOL_INVALID_INPUT",
            message=f"Unknown venue_id={venue_id!r}. Known: {sorted(venue_mods)}",
        )
        output = {"venue_id": venue_id, "error": str(err)}
        record_tool_call("calculate_cost", args, output)
        return ToolResult(
            success=False,
            output=output,
            summary=f"calculate_cost: unknown venue {venue_id!r}",
            error=err,
        )

    venue = next((v for v in venues if v["id"] == venue_id), None)
    if venue is None:
        err = ToolError(
            code="SA_TOOL_INVALID_INPUT",
            message=f"venue_id={venue_id!r} has a catering modifier but no venue record",
        )
        output = {"venue_id": venue_id, "error": str(err)}
        record_tool_call("calculate_cost", args, output)
        return ToolResult(
            success=False,
            output=output,
            summary=f"calculate_cost: stale id {venue_id!r}",
            error=err,
        )

    base_per_head = base_rates[catering_tier]
    venue_mult = venue_mods[venue_id]
    raw_subtotal = base_per_head * venue_mult * party_size * max(1, duration_hours)
    service_charge_percent = catering["service_charge_percent"]
    service = round(raw_subtotal * service_charge_percent / 100)
    min_spend = venue.get("min_spend_gbp", 0)
    hire_fee = venue.get("hire_fee_gbp", 0)
    effective_sub = round(max(raw_subtotal, min_spend))
    total = effective_sub + service + hire_fee

    # Deposit policy
    if total < 300:
        deposit = 0
    elif total <= 1000:
        deposit = round(total * 0.20)
    else:
        deposit = round(total * 0.30)

    output = {
        "venue_id": venue_id,
        "party_size": party_size,
        "duration_hours": duration_hours,
        "catering_tier": catering_tier,
        "subtotal_gbp": effective_sub,
        "service_gbp": service,
        "hire_fee_gbp": hire_fee,
        "total_gbp": total,
        "deposit_required_gbp": deposit,
    }
    summary = f"calculate_cost({venue_id}, {party_size}): total £{total}, deposit £{deposit}"
    record_tool_call("calculate_cost", args, output)
    return ToolResult(success=True, output=output, summary=summary)


# ---------------------------------------------------------------------------
# generate_flyer
# ---------------------------------------------------------------------------
_FLYER_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{venue_name} — {date}</title>
<style>
  body {{ font-family: Georgia, "Times New Roman", serif; max-width: 640px;
         margin: 2em auto; padding: 1.5em; border: 1px solid #999;
         background: #fdfaf3; color: #222; }}
  h1 {{ margin: 0 0 .2em 0; font-size: 1.9em; }}
  .tagline {{ font-style: italic; color: #555; margin: 0 0 1em 0; }}
  dl {{ display: grid; grid-template-columns: 12em 1fr; gap: .3em 1em; }}
  dt {{ font-weight: bold; color: #444; }}
  dd {{ margin: 0; }}
  .total {{ font-size: 1.2em; }}
</style>
</head>
<body>
<article>
  <h1 data-testid="venue_name">{venue_name}</h1>
  <p class="tagline">An Edinburgh evening — booked by your AI agent.</p>

  <dl>
    <dt>Address</dt>      <dd data-testid="venue_address">{venue_address}</dd>
    <dt>Date</dt>         <dd data-testid="date">{date}</dd>
    <dt>Time</dt>         <dd data-testid="time">{time}</dd>
    <dt>Party size</dt>   <dd data-testid="party_size">{party_size}</dd>
    <dt>Weather</dt>      <dd>
        <span data-testid="condition">{condition}</span>,
        <span data-testid="temperature_c">{temperature_c}</span>°C
    </dd>
    <dt>Total</dt>        <dd class="total"><span data-testid="total_gbp">£{total_gbp}</span></dd>
    <dt>Deposit</dt>      <dd><span data-testid="deposit_required_gbp">£{deposit_required_gbp}</span></dd>
  </dl>
</article>
</body>
</html>
"""


def generate_flyer(session: Session, event_details: dict) -> ToolResult:
    """Produce an HTML flyer and write it to workspace/flyer.html.

    event_details is expected to contain at least:
      venue_name, venue_address, date, time, party_size, condition,
      temperature_c, total_gbp, deposit_required_gbp

    Returns:
      output: {"path": "workspace/flyer.html", "bytes_written": int}
      summary: "generate_flyer: wrote <path> (<N> chars)"

    IMPORTANT: this tool MUST be registered with parallel_safe=False
    because it writes a file. We log only metadata (path, bytes_written)
    to _TOOL_CALL_LOG — never the rendered facts — so that the integrity
    check cannot self-verify flyer contents against this entry.
    """
    required = [
        "venue_name",
        "venue_address",
        "date",
        "time",
        "party_size",
        "condition",
        "temperature_c",
        "total_gbp",
        "deposit_required_gbp",
    ]
    missing = [k for k in required if k not in event_details]
    if missing:
        err = ToolError(
            code="SA_TOOL_INVALID_INPUT",
            message=f"event_details missing keys: {missing}",
        )
        output = {"missing_keys": missing, "error": str(err)}
        # log args separately as a sanitized digest (NOT the values themselves)
        record_tool_call("generate_flyer", {"missing": missing}, output)
        return ToolResult(
            success=False, output=output, summary=f"generate_flyer: missing {missing}", error=err
        )

    flyer_html = _FLYER_HTML_TEMPLATE.format(
        venue_name=event_details["venue_name"],
        venue_address=event_details["venue_address"],
        date=event_details["date"],
        time=event_details["time"],
        party_size=event_details["party_size"],
        condition=event_details["condition"],
        temperature_c=event_details["temperature_c"],
        total_gbp=event_details["total_gbp"],
        deposit_required_gbp=event_details["deposit_required_gbp"],
    )

    workspace_dir = session.workspace_dir
    workspace_dir.mkdir(parents=True, exist_ok=True)
    flyer_path = workspace_dir / "flyer.html"
    flyer_path.write_text(flyer_html, encoding="utf-8")

    bytes_written = flyer_path.stat().st_size
    output = {"path": "workspace/flyer.html", "bytes_written": bytes_written}
    # Log args as a digest only (just the keys, no values). This prevents
    # verify_dataflow from "verifying" facts against the flyer-tool's own
    # log entry (circular self-validation).
    sanitised_args = {"keys": sorted(event_details.keys())}
    record_tool_call("generate_flyer", sanitised_args, output)

    return ToolResult(
        success=True,
        output=output,
        summary=f"generate_flyer: wrote {output['path']} ({bytes_written} chars)",
    )


# ---------------------------------------------------------------------------
# Registry builder — DO NOT MODIFY the name, signature, or registration calls.
# ---------------------------------------------------------------------------
def build_tool_registry(session: Session) -> ToolRegistry:
    """Build a session-scoped tool registry with all four Ex5 tools plus
    the sovereign-agent builtins (read_file, write_file, list_files,
    handoff_to_structured, complete_task)."""
    from sovereign_agent.tools.builtin import make_builtin_registry

    reg = make_builtin_registry(session)

    reg.register(
        _RegisteredTool(
            name="venue_search",
            description="Search Edinburgh venues by area, party size, and max budget.",
            fn=venue_search,
            parameters_schema={
                "type": "object",
                "properties": {
                    "near": {"type": "string"},
                    "party_size": {"type": "integer"},
                    "budget_max_gbp": {"type": "integer", "default": 1000},
                },
                "required": ["near", "party_size"],
            },
            returns_schema={"type": "object"},
            is_async=False,
            parallel_safe=True,
            examples=[
                {
                    "input": {"near": "Haymarket", "party_size": 6, "budget_max_gbp": 800},
                    "output": {"count": 1, "results": [{"id": "haymarket_tap"}]},
                }
            ],
        )
    )

    reg.register(
        _RegisteredTool(
            name="get_weather",
            description="Get scripted weather for a city on a YYYY-MM-DD date.",
            fn=get_weather,
            parameters_schema={
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "date": {"type": "string"},
                },
                "required": ["city", "date"],
            },
            returns_schema={"type": "object"},
            is_async=False,
            parallel_safe=True,
            examples=[
                {
                    "input": {"city": "Edinburgh", "date": "2026-04-25"},
                    "output": {"condition": "cloudy", "temperature_c": 12},
                }
            ],
        )
    )

    reg.register(
        _RegisteredTool(
            name="calculate_cost",
            description="Compute total cost and deposit for a booking.",
            fn=calculate_cost,
            parameters_schema={
                "type": "object",
                "properties": {
                    "venue_id": {"type": "string"},
                    "party_size": {"type": "integer"},
                    "duration_hours": {"type": "integer"},
                    "catering_tier": {
                        "type": "string",
                        "enum": ["drinks_only", "bar_snacks", "sit_down_meal", "three_course_meal"],
                        "default": "bar_snacks",
                    },
                },
                "required": ["venue_id", "party_size", "duration_hours"],
            },
            returns_schema={"type": "object"},
            is_async=False,
            parallel_safe=True,
            examples=[
                {
                    "input": {
                        "venue_id": "haymarket_tap",
                        "party_size": 6,
                        "duration_hours": 3,
                    },
                    "output": {"total_gbp": 540, "deposit_required_gbp": 0},
                }
            ],
        )
    )

    def _flyer_adapter(event_details: dict) -> ToolResult:
        return generate_flyer(session, event_details)

    reg.register(
        _RegisteredTool(
            name="generate_flyer",
            description="Write an HTML flyer for the event to workspace/flyer.html.",
            fn=_flyer_adapter,
            parameters_schema={
                "type": "object",
                "properties": {"event_details": {"type": "object"}},
                "required": ["event_details"],
            },
            returns_schema={"type": "object"},
            is_async=False,
            parallel_safe=False,  # writes a file — MUST be False
            examples=[
                {
                    "input": {
                        "event_details": {
                            "venue_name": "Haymarket Tap",
                            "date": "2026-04-25",
                            "party_size": 6,
                        }
                    },
                    "output": {"path": "workspace/flyer.html"},
                }
            ],
        )
    )

    return reg


__all__ = [
    "build_tool_registry",
    "venue_search",
    "get_weather",
    "calculate_cost",
    "generate_flyer",
]
