# Future experiment: nod/shake as an opt-in wake trigger (not implemented)

Tap-to-talk v2 uses only the CAPTOUCH temple tap (`InputEvent.Back`) as its
hands-free trigger. Passive Motion/IMU sensing (nod = yes, shake = cancel) is
**not** implemented and must not be treated as available. This is a proposal
for a future, explicitly opt-in experiment only.

## Why this is not on by default

- **Accidental activation.** A nod or head shake happens constantly in
  ordinary life (looking around, exercising, talking, riding in a vehicle).
  Unlike a deliberate temple tap, gesture recognition over IMU data has a much
  higher false-positive rate, and a false "yes" could submit a question or
  cancel a real one without the wearer intending it.
- **Battery cost.** Continuously sampling and classifying IMU data to detect
  gestures keeps a sensor and classifier running whenever the glasses are
  worn, not just during an active interaction, unlike CAPTOUCH which is
  event-driven.
- **Privacy cost.** Always-on motion sensing is a standing capability that
  could later be repurposed (e.g., activity inference) beyond its stated
  purpose. Any opt-in should be scoped, clearly disclosed, and revocable
  independently of the microphone/CAPTOUCH permissions already in use.

## If this is revisited

- Gate it behind an explicit settings toggle, off by default, separate from
  the CAPTOUCH-based tap-to-talk flow.
- Require a deliberate, low-false-positive gesture threshold validated against
  real wear data (walking, driving, exercising) before enabling by default for
  any user.
- Feed recognized gestures into the same `TapToTalkStateMachine` as new
  events (e.g., a `NodConfirm` / `ShakeCancel` event) rather than a parallel
  control path, so idle/listening/busy semantics stay in one place.
- Document battery impact measured on-device, not estimated.
