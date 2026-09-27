# Ray-Ban Meta Glasses + Hermes

Connect your Ray-Ban Meta glasses to your own Hermes AI agent instead of
Meta's built in assistant. Ask it something out loud on the glasses, it
thinks with your own Hermes agent, and answers back in your own cloned voice.
Everything runs over your private Tailscale network, so it's just your
glasses talking to your own Mac. Nothing routes through Meta's or anyone
else's cloud beyond what the glasses themselves already require.

This is not an official Meta or Nous Research project, I'm not affiliated
with either. I built this because I wanted my glasses to talk to my own
agent, not Meta's.

This is a companion service that connects a phone client to a Hermes Agent
running on your own Mac. It keeps the Meta glasses SDK out of the agent
process and gives mobile clients one stable protocol for:

- persistent Hermes conversations;
- English, Hindi, and French replies;
- local speech-to-text and text-to-speech providers;
- Tailscale-only access when bound to the Mac's Tailscale address.

Everything stays on your own machines: the bridge only accepts requests over
your tailnet (or loopback), and it never proxies to a third-party TTS/STT
cloud unless you configure one yourself.

macOS system voices work out of the box as a fallback. If you want your own
cloned voice answering back instead of a generic robot voice, the bridge also
supports MLX-Audio Chatterbox Multilingual v3, running entirely on your Mac,
in English, Hindi, and French.

The Android companion app is in [`android/`](android/README.md). It uses Meta's
Device Access Toolkit for speech recognition on the glasses, sends final
transcripts to this bridge over Tailscale, and plays authenticated cloned-voice
replies through the phone's active Bluetooth audio route.

## What you need

- **Meta Ray-Ban (or similar Meta AI) glasses**, paired to an Android phone
  with the Meta AI app, Developer Mode enabled on the glasses, and Meta's
  Speech API accepted for your account. Meta currently marks Speech as
  experimental and may gate access, so check the Meta AI app or Meta for
  Developers to see where you stand.
- **A Meta developer app**: register one at
  [developers.meta.com](https://developers.meta.com/) to get your own
  `mwdat_application_id` and `mwdat_client_token` for Device Access Toolkit.
  Meta ships a documented `0`/test credential pair for local development; you
  need your own for anything beyond that.
- **A Mac** (Apple Silicon recommended for Chatterbox voice cloning) already
  running [Hermes Agent](https://github.com/NousResearch/hermes-agent) with
  its API server reachable on loopback.
- **[Tailscale](https://tailscale.com/)** installed and signed into the same
  tailnet on both the Mac and the Android phone. The bridge deliberately
  refuses plain HTTP to anything outside a private/tailnet address, see
  `BridgeEndpoint.kt` and the bridge's own host checks if you want the
  details.
- Python 3.11+ and [`uv`](https://github.com/astral-sh/uv) on the Mac; JDK 17
  and Android SDK 36 to build the Android app.

You don't need an Apple Developer account, a Meta production app review, or
any cloud account beyond your own Hermes and Tailscale setup. Meta's own
Speech API access is the one thing outside this project's control.

## Quick start

1. Run `./scripts/configure_target.py` to generate a mode-0600 `.env` with a
   random bridge key, the active Tailscale IPv4 address, and Hermes's existing
   API key.
2. Enable Hermes's API server on loopback port 8642 using the same
   `HERMES_API_KEY`.
3. Start Hermes with `hermes gateway`.
4. Run the bridge:

   ```sh
   set -a
   source .env
   set +a
   ./scripts/run_bridge.sh
   ```

5. Check `http://127.0.0.1:8787/health`.

For remote access, set `BRIDGE_HOST` to the Mac's Tailscale IP. Keep Hermes on
`127.0.0.1`; only the bridge needs to be reachable from the phone. This target
uses bridge port 8788 because another local service owns 8787.

## Target Mac service

The editable checkout lives under `Documents`, which macOS does not expose to
background launch agents. Install a small runtime copy and persistent service
under `~/.local/share` with:

```sh
./scripts/install_service.sh
./scripts/e2e_target_test.sh
```

The install script preserves the bridge API key across reinstalls. It also
copies a prepared `work/voice-reference/owner-reference.wav`, if present, and
automatically switches the deployed service from the system voice to
Chatterbox.

## Voice-cloning setup

Install the MLX runtime in the isolated project environment:

```sh
UV_CACHE_DIR=/private/tmp/hermes-glasses-uv-cache \
  uv venv --python ~/.hermes/hermes-agent/venv/bin/python .venv
UV_CACHE_DIR=/private/tmp/hermes-glasses-uv-cache \
  uv pip install --python .venv/bin/python 'mlx-audio>=0.4.7,<0.5'
```

Record the owner, benchmark all target languages, then reinstall the service:

```sh
./scripts/record_voice_reference.sh 45
HF_HOME="$PWD/work/voice-models" \
  .venv/bin/python scripts/benchmark_voice.py \
  work/voice-reference/owner-reference.wav \
  --output-dir work/benchmarks/owner-reference
./scripts/install_service.sh
```

If AVFoundation's default audio device is not the microphone, list devices with
`ffmpeg -f avfoundation -list_devices true -i ""` and pass the desired audio
specifier as the second argument to `record_voice_reference.sh`.

## Phone-facing API

All `/v1/*` requests require `Authorization: Bearer <BRIDGE_API_KEY>`.

- `POST /v1/transcribe?language=en` accepts raw WAV/audio bytes and returns
  text. This requires a configured local STT command.
- `POST /v1/turn` accepts JSON such as
  `{"text":"What happened today?","language":"en","speak":true}`.
- `POST /v1/synthesize` accepts JSON such as
  `{"text":"Bonjour","language":"fr"}`.
- `GET /v1/audio/<id>` returns generated audio.

`session_id` returned by `/v1/turn` should be sent back on later turns.

## Local voice command contract

Set `TTS_PROVIDER=command` and define `TTS_COMMAND` as an argument template.
The bridge executes it without a shell. Supported placeholders are:

- `{text_file}`: UTF-8 input text file;
- `{output_file}`: requested output WAV file;
- `{language}`: `en`, `hi`, or `fr`;
- `{reference_audio}`: your voice reference recording.

The process must exit successfully and create `{output_file}`. Example:

```dotenv
TTS_PROVIDER=command
TTS_REFERENCE_AUDIO=/absolute/path/to/my-voice.wav
TTS_COMMAND=/absolute/path/to/python /absolute/path/to/chatterbox_tts.py --text-file {text_file} --output {output_file} --language {language} --reference {reference_audio}
```

The target install generates this command automatically when the owner reference
exists; keys and voice recordings remain outside version control.

The STT command uses the same pattern with `{input_file}`, `{output_file}`, and
`{language}`; it must write the transcript as UTF-8 text.

## Validation

Run the dependency-free test suite with:

```sh
python3 -m unittest discover -s tests -v
```

## Troubleshooting

- **App shows "Bridge URL needs a host" or is blank on first launch**: that's
  expected, there is no default bridge URL baked into the app. Enter your
  Mac's Tailscale IPv4 address (`tailscale ip -4` on the Mac) and the port
  from its `.env` (`BRIDGE_PORT`).
- **"Plain HTTP is allowed only for a Tailscale or local address"**: the app
  refuses `http://` to anything outside `100.64.0.0/10`, `127.0.0.1`,
  `localhost`, or the Android emulator's `10.0.2.2`. Use your Tailscale IP, or
  put a TLS terminating proxy in front of the bridge for anything else.
- **Bridge starts but the phone can't reach it**: confirm both devices are on
  the same tailnet (`tailscale status` on the Mac should list the phone), and
  that `BRIDGE_HOST` in `.env` is the Mac's Tailscale IP, not `127.0.0.1`.
- **Meta glasses won't register / "Speech not available"**: your Meta account
  needs Speech API access, which Meta gates and may not grant immediately.
  Typed questions in the app work independently of glasses registration, so
  use those to verify the rest of the pipeline first.
- **Voice cloning sounds off / falls back to a system voice**: check
  `TTS_PROVIDER` in `.env` and that `work/voice-reference/owner-reference.wav`
  exists; `scripts/benchmark_voice.py` helps compare a reference clip across
  languages before committing to it.
