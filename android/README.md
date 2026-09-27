# Hermes Glasses for Android

This companion app connects Meta Ray-Ban glasses to the private Hermes voice
bridge running on the Mac mini.

## What it does

1. Registers with the Meta AI app through Meta's Device Access Toolkit (DAT).
2. Requests the glasses microphone permission and starts on-device speech
   recognition. Only transcript text crosses from the glasses to the phone.
3. Sends each final transcript to Hermes over the Mac mini's Tailscale address.
4. Downloads the authenticated cloned-voice WAV and plays it through Android's
   current audio route. With the glasses selected for Bluetooth media, the
   response plays through the glasses.

Typed questions are also supported. Use them to test Tailscale and the bridge
before completing Meta registration.

## Build

Requirements: JDK 17 and Android SDK 36.

```sh
cd android
./gradlew test assembleDebug
```

The debug APK is generated at
`app/build/outputs/apk/debug/app-debug.apk`.

## Phone setup

1. Install Tailscale and sign into the same tailnet as the Mac mini.
2. Install the Meta AI app, pair the glasses, and enable Developer Mode for the
   glasses.
3. Install the debug APK with `./gradlew installDebug` or Android Studio.
4. In Hermes Glasses, leave the bridge URL as
   `http://100.106.184.56:8788` and enter the bridge API key from the Mac's
   `~/.hermes/.env`. The app encrypts this key with Android Keystore and does not
   include it in the APK or repository.
5. Tap **Test Mac bridge**, then **Connect Meta glasses**. Complete the Meta AI
   registration and microphone grant.
6. Tap **Start glasses listening**, speak, and wait for the cloned reply.

For the milestone acceptance test, disable Wi-Fi before step 5. A successful
typed question proves the cellular/tailnet/bridge/audio path. A spoken question
then proves the glasses transcription path.

Developer builds use Meta's documented `0` application ID and client token.
Production credentials can be placed in ignored `android/local.properties`:

```properties
mwdat_application_id=your_application_id
mwdat_client_token=your_client_token
```

Meta currently marks Speech as experimental, so this app is suitable for local
development and beta testing, not production release channels.
