# Ripper Tipper prediction pipeline

This directory builds the static prediction snapshot consumed by the Android
app. It uses free data sources and keeps every adjustment explainable.

Current inputs:

- Squiggle fixtures, results and computer-model tips
- Elo ratings rebuilt from completed AFL matches
- Recent five-match form
- Rest days and short turnarounds
- Approximate travel distance
- Open-Meteo venue forecasts
- Optional verified match-week signals in `manual_signals.json`

Run `python backend/update_predictions.py`. The command writes an inspectable
JSON result to `backend/output/current_round.json` and generates the Kotlin
snapshot consumed by the app.

Squiggle consensus carries most weight. Context adjustments are deliberately
small and capped. Weather is reported but does not alter a pick until
back-testing proves that it improves prediction calibration.

