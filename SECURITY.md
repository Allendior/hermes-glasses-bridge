# Security Policy

## Report a vulnerability privately

Please do not open a public issue for a vulnerability involving authentication,
private network access, voice recordings, credentials, or personal data.

Use GitHub's private vulnerability reporting for this repository:

<https://github.com/Allendior/rayban-meta-glasses-hermes/security/advisories/new>

Include the affected commit, a minimal reproduction, the impact, and any fix you
have already tested. Do not attach bridge keys, Hermes keys, `.env` files,
voice-reference recordings, session transcripts, or provider responses.

## Security boundary

The bridge is designed to bind only to loopback or a Tailscale IPv4 address. It
is not designed to face the public internet. Every `/v1/*` request requires a
long random bearer key. Hermes itself should remain bound to loopback.

The Android app allows cleartext HTTP because the first release talks directly
to a Tailscale IP. The app validates that plain HTTP points only to loopback,
the Android emulator host, or `100.64.0.0/10`. If you expose the bridge through
any other network, put authenticated TLS in front of it and use an `https://`
URL.

## Supported versions

Security fixes are applied to the latest commit on `main`. There are no stable
release branches yet.
