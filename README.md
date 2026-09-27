# Hermes Glasses Bridge

This companion service connects a phone client to an existing Hermes Agent on
the Mac mini. It keeps the Meta glasses SDK out of the agent process and gives
the mobile clients one stable protocol for:

- persistent Hermes conversations;
- English, Hindi, and French replies;
- local speech-to-text and text-to-speech providers;
- Tailscale-only access when bound to the Mac's Tailscale address.

The first milestone keeps the macOS system voices as a transport fallback. The
target Mac also has MLX-Audio Chatterbox Multilingual v3 installed for local,
zero-shot voice cloning in English, Hindi, and French.

The Android companion app is in [`android/`](android/README.md). It uses Meta's
Device Access Toolkit for speech recognition on the glasses, sends final
transcripts to this bridge over Tailscale, and plays authenticated cloned-voice
replies through the phone's active Bluetooth audio route.

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
