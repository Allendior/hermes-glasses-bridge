# Contributing

Thanks for helping make this safer and easier to run.

## Before opening a change

1. Open an issue first for large changes or new device support.
2. Keep one logical change per pull request.
3. Never commit credentials, `.env` files, voice recordings, transcripts,
   model caches, APK signing keys, or Android `local.properties`.
4. Treat Meta DAT as a separately licensed dependency. Do not copy its source or
   artifacts into this repository.

## Verify your change

Run the bridge suite:

```sh
python3 -m unittest discover -s tests -v
```

Run the Android checks:

```sh
cd android
./run_gradle.sh test lint assembleDebug
```

If you change dependencies, update `uv.lock` or the Gradle files, then update
`THIRD_PARTY_NOTICES.md`. If you change networking or authentication, explain
the trust boundary and add a regression test.

In the pull request, say what you tested, which operating system and device you
used, and what you could not verify. A screenshot is not a substitute for a
repeatable test.
