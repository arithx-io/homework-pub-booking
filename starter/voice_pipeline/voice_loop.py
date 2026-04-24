"""Ex8 — voice loop.

Text mode runs stdin → manager → stdout.
Voice mode runs mic → Speechmatics → manager → ElevenLabs → speaker.

The trace records EVERY utterance (both directions) as
'voice.utterance_in' (user) and 'voice.utterance_out' (manager).
"""

from __future__ import annotations

import os
import sys

from sovereign_agent.session.directory import Session
from sovereign_agent.session.state import now_utc

from starter.voice_pipeline.manager_persona import ManagerPersona


# ---------------------------------------------------------------------------
# Text mode — implemented; read to learn the shape expected of voice mode
# ---------------------------------------------------------------------------
async def run_text_mode(session: Session, persona: ManagerPersona, max_turns: int = 6) -> None:
    """Run the conversation via stdin/stdout.

    This implementation is COMPLETE (no TODO) so you can see the
    expected trace event shape. Read it, then port the same shape to
    run_voice_mode().
    """
    print("Text mode. Type a message to Alasdair (pub manager); blank line to quit.")
    print(f"Session: {session.session_id}")
    print("-" * 60)

    for turn_idx in range(max_turns):
        try:
            user_text = input("you> ").strip()
        except EOFError:
            break
        if not user_text:
            break

        session.append_trace_event(
            {
                "event_type": "voice.utterance_in",
                "actor": "user",
                "timestamp": now_utc().isoformat(),
                "payload": {"text": user_text, "turn": turn_idx, "mode": "text"},
            }
        )

        manager_text = await persona.respond(user_text)
        print(f"alasdair> {manager_text}")

        session.append_trace_event(
            {
                "event_type": "voice.utterance_out",
                "actor": "manager",
                "timestamp": now_utc().isoformat(),
                "payload": {"text": manager_text, "turn": turn_idx, "mode": "text"},
            }
        )

    print("-" * 60)
    print(f"Conversation ended. Trace: {session.trace_path}")


# ---------------------------------------------------------------------------
# Voice mode — TODO
# ---------------------------------------------------------------------------
async def run_voice_mode(session: Session, persona: ManagerPersona, max_turns: int = 6) -> None:
    """Run the conversation via real STT + TTS.

    Requirements:
      1. Check for SPEECHMATICS_KEY. If missing, print a WARNING and
         fall back to run_text_mode. Do NOT crash.
      2. If ElevenLabs key (ELEVENLABS_API_KEY) is missing, still do
         STT but render the manager's replies as text (print + TTS
         is optional).
      3. Emit the SAME two trace events per turn as text mode:
           voice.utterance_in with payload {"text": ..., "turn": N, "mode": "voice"}
           voice.utterance_out with payload {"text": ..., "turn": N, "mode": "voice"}
      4. End cleanly on silence timeout or 'goodbye' / 'cheerio'.

    You can use sovereign-agent's voice protocol (SpeechmaticsVoicePipeline)
    but it's a skeleton as of v0.2.0 — most students end up calling the
    speechmatics-python client directly. That's fine.
    """
    if not os.environ.get("SPEECHMATICS_KEY"):
        print(
            "⚠  SPEECHMATICS_KEY not set. Falling back to text mode.\n"
            "   See docs/speechmatics-setup.md to enable real voice.",
            file=sys.stderr,
        )
        await run_text_mode(session, persona, max_turns=max_turns)
        return

    # TODO: real voice pipeline.
    #
    # Minimum viable voice mode:
    #   - Open a Speechmatics real-time session (websocket).
    #   - Stream the user's mic to it.
    #   - When Speechmatics emits a final transcript, log and call
    #     persona.respond().
    #   - Print the manager's reply. If you have ELEVENLABS_API_KEY,
    #     also synthesise and play it through the speakers.
    #   - Loop until the user is silent for ~5 seconds or says 'goodbye'.
    #
    # This is the most open-ended part of the homework. Get text mode
    # green first; voice mode is bonus.
    raise NotImplementedError(
        "TODO Ex8 (voice mode): see the docstring for the expected flow. "
        "Graceful degradation to text mode is already handled above."
    )


__all__ = ["run_text_mode", "run_voice_mode"]
