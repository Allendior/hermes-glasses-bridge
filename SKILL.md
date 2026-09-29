---
name: rayban-meta-hermes
description: Connect Ray-Ban Meta glasses to a Hermes agent.
version: 0.1.0
author: Allen Dior (Allendior), Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [Wearables, Ray-Ban, Meta, Android, Voice]
    homepage: https://github.com/Allendior/rayban-meta-glasses-hermes
---

# Ray-Ban Meta Glasses + Hermes Skill

Set up and verify the owner-operated bridge between Meta AI glasses, the Android
companion app, and a Hermes Agent running on a Mac. This skill is setup and
operations guidance. It does not grant Meta developer access or approve public
network exposure.

## When to Use

- The user wants to connect Ray-Ban Meta glasses to their own Hermes Agent.
- The user needs to install, verify, update, or remove the Mac bridge service.
- The user is troubleshooting Meta DAT registration, Tailscale connectivity, or
  local reply audio.

Do not use this skill to bypass Meta account controls, capture another person
without consent, expose Hermes to the public internet, or silently install a
persistent service.

## Prerequisites

- macOS with Hermes Agent already working on loopback.
- Tailscale on the Mac and Android phone, both in the same tailnet.
- An Android phone paired to supported Meta AI glasses.
- Meta Developer Mode and Speech API access for the user's own account.
- JDK 17 and Android SDK 36 for building the companion app.
- An already-exported `API_SERVER_KEY` or `HERMES_API_KEY` matching Hermes.

Never read `~/.hermes/.env`, print a credential, or copy a credential into chat.
Use an already-exported environment value or a vault-mediated flow.

## Procedure

1. Use `read_file` to inspect `README.md`, `SECURITY.md`, and
   `THIRD_PARTY_NOTICES.md`. Stop if the requested deployment contradicts the
   documented trust boundary.
2. Use `terminal` to run `python3 -m unittest discover -s tests -v`. Continue
   only when the bridge tests pass.
3. Use `terminal` with workdir `android/` to run
   `./run_gradle.sh test lint assembleDebug`. Continue only when all three
   checks pass.
4. Use `terminal` to run `./scripts/configure_target.py`. The user must provide
   the Hermes API key through their secure environment, never through chat.
5. Use `terminal` to run `./scripts/install_service.sh --dry-run`. Show the
   exact runtime path, LaunchAgent path, persistence, and uninstall command.
6. Ask for explicit approval before running `./scripts/install_service.sh`.
   Recording or copying a voice reference requires separate explicit approval.
7. Have the user enter their own bridge URL and bridge key in the Android app.
   Do not bake either value into source, an APK, an issue, or a log.
8. Use `terminal` to run `./scripts/e2e_target_test.sh`. Report real output and
   distinguish bridge verification from physical glasses verification.

## Security Boundary

- `BRIDGE_HOST` must be loopback or a Tailscale IPv4 address in
  `100.64.0.0/10`.
- Hermes stays on loopback. Only the bridge is reachable from the tailnet.
- Every `/v1/*` request requires the bridge bearer key.
- Meta handles the glasses SDK and speech features. Hermes uses the model
  provider selected by the owner. Do not describe the full system as local-only
  unless each configured component is actually local.
- Never publish keys, `.env` files, voice references, transcripts, Android
  `local.properties`, or model caches.

## Pitfalls

- Meta can gate Speech API access even when the app builds correctly.
- Android permits cleartext HTTP for direct Tailscale IPs. Never use plain HTTP
  to a LAN or public address.
- The cloned voice model is large and first use may download model files.
- A successful Android build does not prove the physical glasses path works.
- The uninstall script removes the service but preserves runtime data to avoid
  silently deleting keys or voice recordings.

## Verification

A complete verification includes all of the following:

- Python tests pass.
- Android unit tests, lint, and debug assembly pass.
- `BRIDGE_HOST` is loopback or the owner's Tailscale IPv4 address.
- `/health` succeeds.
- An authenticated persistent Hermes turn succeeds.
- Generated audio downloads successfully.
- The user confirms the reply plays through their glasses.
- `git status` shows no credential, voice, model-cache, APK, or local-properties
  artifact staged for commit.
