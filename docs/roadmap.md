# Ripper Tipper roadmap

## Done

- Android-first Kotlin/Jetpack Compose app.
- Simple pick-first UI with expandable reasoning.
- Free-data prediction pipeline.
- Injury, availability, weather, form, power-ranking and upset-risk inputs.
- Live round rollover fallback on-device.
- GitHub Actions workflow for hosted prediction refresh.
- GitHub Pages JSON endpoint for the app to consume.

## Next

- Enable GitHub Pages in repository settings if the first workflow run asks for
  it.
- Confirm the hosted endpoint is live:
  `https://langzonedev.github.io/RipperTipper/current_round.json`.
- Add model back-testing so weighting changes can be measured against past
  rounds instead of tuned by vibes.
- Add a lightweight prediction accuracy report after each round.
- Prepare Play Store production signing, privacy policy and tester onboarding.

## Later

- Move from GitHub Pages to Cloudflare/Firebase only if refresh frequency,
  private controls, or richer APIs outgrow the simple static JSON endpoint.
- Add opt-in notifications near lockout if a pick changes materially.
- Add iOS only if Android testing proves the product is worth widening.
