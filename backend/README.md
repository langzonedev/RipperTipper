# Ripper Tipper prediction pipeline

This directory builds the static prediction snapshot consumed by the Android
app. It uses free data sources and keeps every adjustment explainable.

Current inputs:

- Squiggle fixtures, results and computer-model tips
- Squiggle power rankings from the most recently completed round
- Elo ratings rebuilt from completed AFL matches
- Recent five-match form
- Recent scoring margins
- Venue tendency
- Rest days and short turnarounds
- Approximate travel distance
- Open-Meteo venue forecasts
- AFL.com.au injury list and weekly "in the mix" availability notes
- Optional verified match-week signals in `manual_signals.json`

Run `python backend/update_predictions.py`. The command writes an inspectable
JSON result to `backend/output/current_round.json` and generates the Kotlin
snapshot consumed by the app.

Squiggle consensus carries most weight. Context adjustments are deliberately
small and capped. The model also applies a small upset-risk drag to fragile
favourites when the market is split, weather is messy, or recent form is
arguing against the pick.
