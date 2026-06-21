# Ripper Tipper

Ripper Tipper is an Android-first AFL tipping assistant for people who do not
want to spend their week thinking about AFL. It gives one clear recommendation
for every match, with a confidence level and optional supporting detail.

## Current state

The first milestone is a native Kotlin and Jetpack Compose application containing:

- a clean current-round screen;
- one recommended team per match;
- visible prediction confidence;
- expandable reasoning;
- sample data while the live prediction service is built.

The on-screen predictions are placeholders and must not yet be used as real tips.

## Run locally

1. Install the latest stable Android Studio.
2. Install Android SDK Platform 36 from SDK Manager.
3. Open this repository in Android Studio and allow Gradle to sync.
4. Run the `app` configuration on an emulator or connected Android phone.

The application supports Android 8.0 (API 26) and newer.

## Install on an Android phone

For private testing, download `install/RipperTipper-0.1.0-debug.apk` directly
from this repository on the phone. Android may ask you to allow the browser or
GitHub app to install unknown apps. This is a development build and is not a
Google Play release.

## Planned architecture

The Android app will remain a focused presentation client. A separate backend
will collect fixtures, results, model predictions and time-sensitive reports,
then expose Ripper Tipper's final recommendations through a small API.

Initial public fixture and prediction data will be sourced server-side from
Squiggle in accordance with its caching and identification requirements.
