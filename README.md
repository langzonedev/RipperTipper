# Ripper Tipper

Ripper Tipper is an Android-first AFL tipping assistant for people who do not
want to spend their week thinking about AFL. It gives one clear recommendation
for every match, with a confidence level and optional supporting detail.

## Current state

The app is a native Kotlin and Jetpack Compose Android application containing:

- a clean current-round screen;
- one recommended team per match;
- visible prediction confidence;
- expandable reasoning;
- hosted prediction refresh through GitHub Pages;
- baked and on-device fallbacks if the hosted endpoint is unavailable.

The app checks the hosted prediction JSON first, then falls back to the baked
APK snapshot and direct Squiggle round rollover.

## Hosted prediction data

GitHub Actions runs the backend on a schedule and commits the latest generated
tips to:

```text
public/current_round.json
```

The Android app checks the GitHub Pages endpoint first:

```text
https://langzonedev.github.io/RipperTipper/current_round.json
```

It can also fall back to raw GitHub:

```text
https://raw.githubusercontent.com/langzonedev/RipperTipper/main/public/current_round.json
```

## Run locally

1. Install the latest stable Android Studio.
2. Install Android SDK Platform 36 from SDK Manager.
3. Open this repository in Android Studio and allow Gradle to sync.
4. Run the `app` configuration on an emulator or connected Android phone.

The application supports Android 8.0 (API 26) and newer.

## Install on an Android phone

For private testing, download `install/RipperTipper-latest-debug.apk` directly
from this repository on the phone. Android may ask you to allow the browser or
GitHub app to install unknown apps. This is a development build and is not a
Google Play release.

## Architecture

The Android app remains a focused presentation client. A scheduled GitHub
Actions backend collects fixtures, results, model predictions and
time-sensitive reports, then writes Ripper Tipper's final recommendations as a
small JSON file.

The current free-data pipeline rebuilds Elo team strength from completed
matches, compares recent form and rest, estimates travel, checks venue weather,
reads AFL injury/availability notes, applies an upset-risk adjustment, and
generates a short explanation for every recommendation. Its inspectable output
is stored in `backend/output/current_round.json`.

See `docs/architecture.md` for the hosted backend flow.
