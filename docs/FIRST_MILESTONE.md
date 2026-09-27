# First milestone status

## Completed and verified

- A dependency-free Mac bridge accepts authenticated requests from a future
  iOS or Android client.
- It creates and continues native Hermes sessions through Hermes's supported
  session API.
- It supports per-turn English, Hindi, and French selection.
- It exposes separate transcription, conversation, synthesis, and audio-fetch
  endpoints.
- It has a local command-provider contract for speech recognition and cloned
  speech, so voice engines can change without changing either mobile app.
- The Mac system-voice fallback generated audio successfully in all three
  languages.
- Automated tests verify language validation, persistent conversations, and
  cloned-voice command integration.

## Target Mac mini deployment (2026-09-26)

Completed:

- `./scripts/check_target_mac.sh` passes on the M4/16 GB target.
- Hermes has a strong API key and now listens only on `127.0.0.1:8642`.
- The persistent bridge launch agent listens only on the Mac mini's Tailscale
  IPv4 address, port 8788. The LAN address refuses both ports.
- MLX-Audio 0.4.8 and Chatterbox Multilingual v3 are installed in an isolated
  environment. A non-owner sample verified English, Hindi, French, and mixed
  generation. The initial download/cold run took 129.356 seconds; cached runs
  took 8.059–8.773 seconds (2.099–2.215 real-time factor).
- A real authenticated question passed through the Tailscale-bound bridge to
  Hermes. A French follow-up reused the same native Hermes session, and the
  generated audio was fetched successfully.
- The owner supplied English and Hindi recordings. Both were converted to
  lossless, level-balanced 20-second working references and benchmarked across
  English, Hindi, French, and mixed text. The English reference was the most
  consistent across languages and is now active in the persistent bridge.
- The deployed command-provider path generated valid 24 kHz mono WAV output in
  English, Hindi, and French using the owner's reference.
- An Android companion app now integrates Meta's Device Access Toolkit 1.0.0,
  accepts on-glasses English/Hindi/French transcripts, calls the authenticated
  bridge over Tailscale, preserves Hermes sessions, and plays the cloned reply.
  It also includes a typed fallback and a bridge health check for phone-only
  acceptance testing. The API key is entered at runtime and protected by
  Android Keystore; it is not embedded in the APK.
- Android unit tests, lint, debug/release builds, and an Android 15 emulator
  cold-launch all pass. The installed app reached the live Tailscale-bound Mac
  service and reported `Bridge ok; Hermes reachable`.

Remaining human acceptance checks:

1. Listen to the generated English, Hindi, and French samples and confirm that
   speaker similarity and pronunciation are acceptable.
2. Install the Android app from `android/app/build/outputs/apk/debug/app-debug.apk`.
   From the phone with Wi-Fi disabled and Tailscale connected, use **Ask Hermes**
   and confirm cloned-voice playback. This proves the cellular/tailnet path
   rather than only the Mac's local Tailscale interface.

## Acceptance test

The milestone is complete when the two human checks above pass: a phone on
cellular data can send a question over Tailscale, Hermes answers in a persistent
session, and the phone plays the answer in the owner's cloned voice. The phone
must not be able to reach Hermes directly; it only receives the bridge API key.

## Voice reference recording

Use a quiet room and the phone's normal recorder. Record 30–60 seconds in each
language, plus one mixed-language sample. Speak naturally, leave short pauses
between sentences, and avoid music, echo, noise reduction, or another speaker.
Keep the original lossless recording. The first benchmark should also test a
clean 10–20-second excerpt because the engine may perform better with a shorter
reference.
