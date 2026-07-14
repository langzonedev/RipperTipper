# Ripper Tipper roadmap

## Done

- Android-first Kotlin/Jetpack Compose app.
- Simple pick-first UI with expandable reasoning.
- Free-data prediction pipeline.
- Injury, availability, weather, form, power-ranking and upset-risk inputs.
- Live round rollover fallback on-device.
- GitHub Actions workflow for hosted prediction refresh.
- GitHub Actions workflow that commits refreshed prediction JSON.

## Next

- Confirm the GitHub Pages endpoint is live from the phone.
- Add model back-testing so weighting changes can be measured against past
  rounds instead of tuned by vibes.
- Add a lightweight prediction accuracy report after each round.
- Prepare Play Store production signing, privacy policy and tester onboarding.

## Later

- Move from raw GitHub JSON to GitHub Pages, Cloudflare or Firebase only if
  refresh frequency, private controls, or richer APIs outgrow the simple static
  JSON endpoint.
- Add opt-in notifications near lockout if a pick changes materially.
- Add iOS only if Android testing proves the product is worth widening.
