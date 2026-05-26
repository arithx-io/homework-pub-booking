#!/usr/bin/env python3
"""Generate an Ex8 voice-mode session.

Pipeline per turn:
  user_text  -> espeak-ng .wav -> Speechmatics batch STT -> transcript
  transcript -> ManagerPersona (Llama-3.3-70B via Nebius) -> reply
  reply      -> ElevenLabs TTS (logs success/failure)

Emits the same trace-event shape as starter/voice_pipeline/voice_loop.py
run_voice_mode does (voice.utterance_in / voice.utterance_out with
payload {text, turn, mode: "voice"}). Persists the session under
sessions/homework/ex8-voice-pipeline/.

We use espeak-ng as a synthetic mic input because the sandbox has no
audio device. The Speechmatics call is real (batch transcription, not
mocked), the LLM call is real (Nebius), and the ElevenLabs TTS attempt
is real (it may 401 on free-tier-blocked accounts, in which case the
manager reply is printed rather than spoken; that matches the graceful
degradation path in voice_loop.py).
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

# Make starter importable.
sys.path.insert(0, str(Path(__file__).parent.parent))

from sovereign_agent.session.directory import create_session
from sovereign_agent.session.state import now_utc

from starter.voice_pipeline.manager_persona import ManagerPersona

USER_LINES = [
    "Hi, I'd like to book a table for six people next Saturday at seven thirty in the evening.",
    "Two hundred pound deposit, and we'll go for bar snacks.",
    "Yes, please confirm it.",
    "Thanks. Could you give me a reference number?",
]


def synthesize_user_audio(text: str, out_wav: Path) -> None:
    """Render user-side speech via piper-tts (local neural TTS, no API).

    Piper's natural-sounding voice survives Speechmatics STT far better
    than espeak-ng's robotic synthesis. We use the en_GB-alba-medium
    model (a UK-English voice).
    """
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    model_path = "/tmp/piper_models/en_GB-alba-medium.onnx"
    proc = subprocess.run(  # noqa: F841 - holds stderr for debugging on failure
        ["python", "-m", "piper", "--model", model_path, "--output_file", str(out_wav)],
        input=text.encode(),
        check=True,
        capture_output=True,
    )


def transcribe_with_speechmatics(wav_path: Path, api_key: str) -> str:
    """Submit a wav file to Speechmatics batch and return the transcript."""
    base = "https://asr.api.speechmatics.com/v2/jobs/"
    headers = {"Authorization": f"Bearer {api_key}"}
    config = {
        "type": "transcription",
        "transcription_config": {"language": "en"},
    }
    files = {
        "config": (None, json.dumps(config), "application/json"),
        "data_file": (wav_path.name, wav_path.read_bytes(), "audio/wav"),
    }
    resp = requests.post(base, headers=headers, files=files, timeout=30)
    resp.raise_for_status()
    job_id = resp.json()["id"]

    # Poll until done
    for _ in range(40):
        time.sleep(2)
        r = requests.get(f"{base}{job_id}", headers=headers, timeout=15)
        r.raise_for_status()
        status = r.json()["job"]["status"]
        if status == "done":
            break
        if status == "rejected":
            raise RuntimeError(f"Speechmatics rejected job {job_id}")
    else:
        raise TimeoutError(f"Speechmatics job {job_id} never finished")

    txt = requests.get(f"{base}{job_id}/transcript?format=txt", headers=headers, timeout=15)
    txt.raise_for_status()
    return txt.text.strip()


def try_elevenlabs_tts(text: str, api_key: str, out_mp3: Path) -> tuple[bool, str]:
    """Best-effort ElevenLabs TTS. Returns (success, info_message)."""
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    body = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.75},
    }
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=30)
        if resp.status_code == 200:
            out_mp3.parent.mkdir(parents=True, exist_ok=True)
            out_mp3.write_bytes(resp.content)
            return True, f"mp3 written ({len(resp.content)} bytes)"
        return False, f"HTTP {resp.status_code}: {resp.text[:140]}"
    except Exception as e:
        return False, f"exception: {e}"


async def main() -> int:
    speech_key = os.environ.get("SPEECHMATICS_KEY", "").strip()
    eleven_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    nebius_key = os.environ.get("NEBIUS_KEY", "").strip()
    if not speech_key:
        print("✗ SPEECHMATICS_KEY missing", file=sys.stderr)
        return 1
    if not nebius_key:
        print("✗ NEBIUS_KEY missing", file=sys.stderr)
        return 1

    sessions_root = Path("sessions/homework/ex8-voice-pipeline")
    sessions_root.mkdir(parents=True, exist_ok=True)

    session = create_session(
        scenario="ex8-voice-pipeline",
        task=(
            "Voice-mode booking dialog with Alasdair MacLeod, the Haymarket Tap "
            "manager. User books a table; manager validates against policy and "
            "issues a reference."
        ),
        sessions_dir=sessions_root,
    )
    print(f"📂 session: {session.session_id}")
    print(f"   dir:     {session.directory}")

    persona = ManagerPersona.from_env()
    workspace = session.workspace_dir
    workspace.mkdir(parents=True, exist_ok=True)

    tts_attempts: list[dict] = []

    for turn_idx, user_line in enumerate(USER_LINES):
        # ── User utterance: espeak-ng → wav → Speechmatics STT ─────
        user_wav = workspace / f"turn_{turn_idx}_user.wav"
        synthesize_user_audio(user_line, user_wav)
        user_text = transcribe_with_speechmatics(user_wav, speech_key)
        print(f"🎙  user[{turn_idx}]: {user_text!r}")

        session.append_trace_event(
            {
                "event_type": "voice.utterance_in",
                "actor": "user",
                "timestamp": now_utc().isoformat(),
                "payload": {"text": user_text, "turn": turn_idx, "mode": "voice"},
            }
        )

        # ── Manager reply via persona ──────────────────────────────
        manager_text = await persona.respond(user_text)
        print(f"💬 alasdair[{turn_idx}]: {manager_text!r}")

        session.append_trace_event(
            {
                "event_type": "voice.utterance_out",
                "actor": "manager",
                "timestamp": now_utc().isoformat(),
                "payload": {"text": manager_text, "turn": turn_idx, "mode": "voice"},
            }
        )

        # ── ElevenLabs TTS attempt (graceful-degradation path) ─────
        reply_mp3 = workspace / f"turn_{turn_idx}_reply.mp3"
        if eleven_key:
            ok, info = try_elevenlabs_tts(manager_text, eleven_key, reply_mp3)
            tts_attempts.append({"turn": turn_idx, "success": ok, "info": info})
            print(f"🔊 tts[{turn_idx}]: success={ok} ({info[:80]})")
        else:
            tts_attempts.append({"turn": turn_idx, "success": False, "info": "no key"})

    # One audit event summarising the TTS outcome for the run.
    session.append_trace_event(
        {
            "event_type": "voice.tts_summary",
            "actor": "voice-loop",
            "timestamp": now_utc().isoformat(),
            "payload": {
                "provider": "elevenlabs",
                "attempts": tts_attempts,
                "all_successful": all(a["success"] for a in tts_attempts),
            },
        }
    )

    # Move the session to a terminal state via the allowed path.
    session.update_state(state="executing")
    session.mark_complete({"turns": len(USER_LINES), "tts_attempts": tts_attempts})

    print(f"\n✓ done: {session.session_id}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
