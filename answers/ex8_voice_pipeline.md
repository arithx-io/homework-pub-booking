# Ex8 — Voice pipeline

## Your answer

`voice_loop.py` exposes two modes sharing one trace contract:

- `run_text_mode` (primary gradeable path): stdin → `ManagerPersona` →
  stdout. Emits `voice.utterance_in` and `voice.utterance_out` trace
  events per turn with `payload: {text, turn, mode: "text"}`.
- `run_voice_mode`: mic capture via `sounddevice` → Speechmatics
  realtime STT (websocket) → manager reply → **ElevenLabs TTS**
  (per ASSIGNMENT.md §Ex8 line 184) → `pydub` MP3 decode →
  `sounddevice` playback. Same trace event shape with `mode: "voice"`.

**ASSIGNMENT.md says ElevenLabs for TTS, not Rime.** The starter
scaffold (and PR #18) reference Rime — I replaced `_speak_rime`'s
HTTP POST with a real ElevenLabs implementation
(`POST /v1/text-to-speech/{voice_id}`, `model_id=eleven_multilingual_v2`,
voice George ID `JBFqnCBsd6RMkjVDRZzb` matching the gruff Edinburgh
manager persona). Kept `_speak_rime` as a thin shim forwarding to
`_speak_elevenlabs` so existing call sites and `.env` files using
`RIME_API_KEY` continue to work.

**Cohort fix: mic threshold 500 → 250.** vianu's Discord report
(May 22) noted that the upstream RMS threshold of 500 required
users to practically shout before the VAD started capturing. 250
is the cohort-tested sweet spot for typical room noise.

**Graceful degradation, three layers:**
1. No `SPEECHMATICS_KEY` → warn, call `run_text_mode` (still gradeable).
2. `speechmatics` or `sounddevice` import fails → warn, call
   `run_text_mode`.
3. No `ELEVENLABS_API_KEY` (or legacy `RIME_API_KEY`) → STT still
   works, manager replies printed not spoken.

`ManagerPersona` is system-prompted as Alasdair MacLeod, Haymarket
Tap manager, with explicit rules (party ≤ 8, deposit ≤ £300).
Llama-3.3-70B at `temperature=0.0` keeps replies deterministic.
Session `sess_92851b66ea4b` shows a 4-turn text exchange where the
live model handled an in-policy booking entirely in character. Turn 0
(user): *"book a table for 6 next Saturday at 19:30, £200 deposit,
bar snacks"*. Turn 0 (Alasdair): *"Aye, we can do that. I'll pencil
you in for next Saturday at 19:30. What's the contact number?"*
Turns 1–3 walk through catering options, confirm the booking
("Aye, confirmed for next Saturday at 19:30"), and emit a reference
(`HM123`). All four turns carry `mode: "text"` in their trace
payloads. Note the Scots dialect ("Aye", "gie ye the details") —
that's the persona system prompt working.

## Citations

- `starter/voice_pipeline/voice_loop.py` — `run_text_mode`,
  `run_voice_mode`, `_speak_elevenlabs`, `_speak_rime` shim,
  threshold=250
- `starter/voice_pipeline/manager_persona.py` — `ManagerPersona`,
  `MANAGER_SYSTEM_PROMPT` (rules section intact)
- `sessions/homework/ex8/sess_92851b66ea4b/logs/trace.jsonl` — four
  `voice.utterance_in` + four `voice.utterance_out` events, all
  `mode: "text"`, Alasdair consistently in character across turns.
