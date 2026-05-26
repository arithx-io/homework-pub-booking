# Ex8 - Voice pipeline

## Your answer

`voice_loop.py` has two modes that share one trace contract:

- `run_text_mode` (the primary gradeable path): stdin → `ManagerPersona`
  → stdout. Emits `voice.utterance_in` and `voice.utterance_out` trace
  events per turn with `payload: {text, turn, mode: "text"}`.
- `run_voice_mode`: mic capture via `sounddevice` → Speechmatics
  realtime STT (websocket) → manager reply → **ElevenLabs TTS**
  (`POST /v1/text-to-speech/{voice_id}`, `model_id=
  eleven_multilingual_v2`, voice George `JBFqnCBsd6RMkjVDRZzb` for the
  Edinburgh manager persona) → `pydub` MP3 decode → playback. Same
  trace shape, with `mode: "voice"`.

ASSIGNMENT.md §Ex8 line 184 specifies "Speechmatics for STT and
ElevenLabs for TTS". The starter scaffold (and PR #18) referenced
Rime. I replaced `_speak_rime`'s HTTP POST with a real ElevenLabs
implementation and kept `_speak_rime` as a thin shim that forwards to
`_speak_elevenlabs`, so existing `.env` files with `RIME_API_KEY`
continue to work.

vianu's Discord report (May 22) flagged that the upstream RMS mic
threshold of 500 effectively required users to shout. 250 is the
cohort-tested value for typical room noise.

Graceful degradation, three layers:

1. No `SPEECHMATICS_KEY` → warn, fall through to `run_text_mode`.
2. `speechmatics` or `sounddevice` import fails → warn, fall through
   to `run_text_mode`.
3. No `ELEVENLABS_API_KEY` → STT still works; manager replies are
   printed rather than spoken.

`ManagerPersona` is system-prompted as Alasdair MacLeod, Haymarket
Tap manager, with explicit rules (party ≤ 8, deposit ≤ £300).
Llama-3.3-70B at `temperature=0.0` keeps replies stable. Session
`sess_92851b66ea4b` is a 4-turn text exchange where the live model
handled an in-policy booking entirely in character. Turn 0 (user):
*"book a table for 6 next Saturday at 19:30, £200 deposit, bar
snacks"*. Turn 0 (Alasdair): *"Aye, we can do that. I'll pencil you
in for next Saturday at 19:30. What's the contact number?"* Turns
1-3 walk through catering, confirm the booking (*"Aye, confirmed for
next Saturday at 19:30"*), and emit reference `HM123`. Alasdair speaks
in Scots dialect ("Aye", "gie ye the details") the way the system
prompt asks for.

The voice-mode counterpart is captured in `sess_928a3ebed75d` (4 turns,
all `mode: "voice"`). Each user utterance was rendered to audio,
transcribed by Speechmatics' batch STT, then routed through the same
`ManagerPersona`. Real STT artifacts show through in the transcripts
("730" for "seven thirty", "Â£200" with a currency encoding glitch),
which the persona handles gracefully and still drives the booking to a
confirmed reference (`HM001`). The ElevenLabs TTS step on this
particular run logged HTTP 401 (free-tier abuse-detector flagging the
egress IP), so the reply path degraded to print-only per the design
above; the trace records the attempt outcome in `voice.tts_summary`.

## Citations

- `starter/voice_pipeline/voice_loop.py`: `run_text_mode`,
  `run_voice_mode`, `_speak_elevenlabs`, `_speak_rime` shim,
  threshold=250.
- `starter/voice_pipeline/manager_persona.py`: `ManagerPersona`,
  `MANAGER_SYSTEM_PROMPT` (rules section intact).
- `sessions/homework/ex8/sess_92851b66ea4b/logs/trace.jsonl`: four
  `voice.utterance_in` + four `voice.utterance_out` events, all
  `mode: "text"`, Alasdair consistently in character.
- `sessions/homework/ex8-voice-pipeline/sess_928a3ebed75d/logs/trace.jsonl`:
  four `voice.utterance_in` + four `voice.utterance_out` events, all
  `mode: "voice"`, with real Speechmatics-derived transcripts and
  per-turn TTS attempt outcomes.
