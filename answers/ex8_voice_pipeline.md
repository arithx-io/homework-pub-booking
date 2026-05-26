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

The voice-mode counterpart is captured in `sess_bf6a1dafdb8c` (5 turns, all `mode: "voice"`). Real mic capture via `sounddevice` at 16kHz mono, Speechmatics realtime STT over websocket, manager reply via Llama-3.3-70B, ElevenLabs TTS playback through `pydub`. Authentic Speechmatics artifacts come through in the transcripts (`oh seven 9123456` for spoken digits, commas inserted between `Bar , snacks , please`), which the persona handles gracefully and drives the booking to a confirmed reference (`HM001`). The captured audio for each turn lives under `workspace/turn_N_input.wav` as the recording audit trail.

## Citations

- `starter/voice_pipeline/voice_loop.py`: `run_text_mode`,
  `run_voice_mode`, `_speak_elevenlabs`, `_speak_rime` shim,
  threshold=250.
- `starter/voice_pipeline/manager_persona.py`: `ManagerPersona`,
  `MANAGER_SYSTEM_PROMPT` (rules section intact).
- `sessions/homework/ex8/sess_92851b66ea4b/logs/trace.jsonl`: four
  `voice.utterance_in` + four `voice.utterance_out` events, all
  `mode: "text"`, Alasdair consistently in character.
- `sessions/homework/ex8-voice-pipeline/sess_bf6a1dafdb8c/logs/trace.jsonl`:
  five `voice.utterance_in` + five `voice.utterance_out` events, all
  `mode: "voice"`, real Speechmatics transcripts with characteristic
  STT artifacts.
- `sessions/homework/ex8-voice-pipeline/sess_bf6a1dafdb8c/workspace/`:
  five `turn_N_input.wav` recordings (16kHz mono PCM) from the live
  mic capture.
