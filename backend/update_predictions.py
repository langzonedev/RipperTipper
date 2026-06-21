"""Build the current Ripper Tipper snapshot from free data sources."""

from __future__ import annotations

import json
import math
import statistics
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "backend/output/current_round.json"
KOTLIN_OUTPUT = ROOT / (
    "app/src/main/java/com/langzonedev/rippertipper/data/PredictionSnapshot.kt"
)
MANUAL_SIGNALS = ROOT / "backend/manual_signals.json"
SQUIGGLE = "https://api.squiggle.com.au/"
OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
USER_AGENT = (
    "RipperTipper/0.2 "
    "(https://github.com/langzonedev/RipperTipper; "
    "contact: 202942822+langzonedev@users.noreply.github.com)"
)
MELBOURNE = ZoneInfo("Australia/Melbourne")
ADELAIDE = ZoneInfo("Australia/Adelaide")

TEAM_HOME = {
    "Adelaide": (-34.9155, 138.5962),
    "Brisbane Lions": (-27.4858, 153.0381),
    "Carlton": (-37.7839, 144.9614),
    "Collingwood": (-37.8165, 144.9475),
    "Essendon": (-37.7510, 144.9167),
    "Fremantle": (-31.9505, 115.8605),
    "Geelong": (-38.1582, 144.3548),
    "Gold Coast": (-28.0064, 153.3669),
    "Greater Western Sydney": (-33.8430, 151.0670),
    "Hawthorn": (-37.8165, 144.9475),
    "Melbourne": (-37.8165, 144.9475),
    "North Melbourne": (-37.8165, 144.9475),
    "Port Adelaide": (-34.9155, 138.5962),
    "Richmond": (-37.8165, 144.9475),
    "St Kilda": (-37.8165, 144.9475),
    "Sydney": (-33.8917, 151.2247),
    "West Coast": (-31.9505, 115.8605),
    "Western Bulldogs": (-37.8165, 144.9475),
}

VENUES = {
    "Adelaide Oval": (-34.9155, 138.5962, "Adelaide Oval"),
    "Carrara": (-28.0064, 153.3669, "People First Stadium"),
    "Docklands": (-37.8165, 144.9475, "Marvel Stadium"),
    "Gabba": (-27.4858, 153.0381, "Gabba"),
    "Kardinia Park": (-38.1582, 144.3548, "GMHBA Stadium"),
    "M.C.G.": (-37.8199, 144.9834, "MCG"),
    "Manuka Oval": (-35.3183, 149.1345, "Manuka Oval"),
    "Perth Stadium": (-31.9512, 115.8890, "Optus Stadium"),
    "S.C.G.": (-33.8917, 151.2247, "SCG"),
    "Sydney Showground": (-33.8430, 151.0670, "ENGIE Stadium"),
    "York Park": (-41.4258, 147.1389, "UTAS Stadium"),
}


@dataclass
class TeamState:
    elo: float = 1500.0
    recent: list[int] = field(default_factory=list)
    last_game: datetime | None = None


def fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def squiggle(query: str) -> dict[str, Any]:
    return fetch_json(f"{SQUIGGLE}?{query}")


def game_time(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=MELBOURNE)


def next_round(year: int) -> tuple[int, list[dict[str, Any]]]:
    games = squiggle(f"q=games;year={year}")["games"]
    now = datetime.now(timezone.utc)
    future = [
        game
        for game in games
        if not game.get("is_final")
        and game.get("ateam")
        and game.get("hteam")
        and game_time(game["date"]).astimezone(timezone.utc) > now
    ]
    round_number = min(int(game["round"]) for game in future)
    selected = [game for game in future if int(game["round"]) == round_number]
    return round_number, sorted(selected, key=lambda game: game["date"])


def completed_games(start_year: int, end_year: int, cutoff: datetime) -> list[dict[str, Any]]:
    result = []
    for year in range(start_year, end_year + 1):
        for game in squiggle(f"q=games;year={year}")["games"]:
            if (
                game.get("complete") == 100
                and game.get("ateam")
                and game.get("hteam")
                and game_time(game["date"]) < cutoff
            ):
                result.append(game)
    return sorted(result, key=lambda game: game["date"])


def build_states(games: list[dict[str, Any]]) -> dict[str, TeamState]:
    states: dict[str, TeamState] = {}
    for game in games:
        away = states.setdefault(game["ateam"], TeamState())
        home = states.setdefault(game["hteam"], TeamState())
        expected_home = 1 / (1 + 10 ** ((away.elo - home.elo - 45) / 400))
        actual_home = 1.0 if game["hscore"] > game["ascore"] else 0.0
        if game["hscore"] == game["ascore"]:
            actual_home = 0.5
        multiplier = math.log(abs(game["hscore"] - game["ascore"]) + 1) * 0.75 + 1
        change = 20 * multiplier * (actual_home - expected_home)
        home.elo += change
        away.elo -= change
        home.recent = (home.recent + [int(actual_home == 1)])[-5:]
        away.recent = (away.recent + [int(actual_home == 0)])[-5:]
        played = game_time(game["date"])
        home.last_game = played
        away.last_game = played
    return states


def consensus(year: int, round_number: int) -> dict[int, dict[str, Any]]:
    grouped: dict[int, list[dict[str, Any]]] = {}
    for tip in squiggle(f"q=tips;year={year};round={round_number}")["tips"]:
        if tip.get("tip") and tip.get("confidence") is not None:
            grouped.setdefault(int(tip["gameid"]), []).append(tip)

    result = {}
    for game_id, tips in grouped.items():
        home_name = tips[0]["hteam"]
        home_probabilities = [
            float(tip["confidence"]) if tip["tip"] == home_name
            else 100 - float(tip["confidence"])
            for tip in tips
        ]
        result[game_id] = {
            "model_count": len(tips),
            "home_probability": statistics.fmean(home_probabilities) / 100,
            "home_tip_count": sum(tip["tip"] == home_name for tip in tips),
        }
    return result


def haversine_km(origin: tuple[float, float], destination: tuple[float, float]) -> int:
    lat1, lon1 = map(math.radians, origin)
    lat2, lon2 = map(math.radians, destination)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    value = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return round(6371 * 2 * math.asin(math.sqrt(value)))


def forecast(game: dict[str, Any]) -> dict[str, Any] | None:
    venue = VENUES.get(game["venue"])
    if not venue:
        return None
    day = game_time(game["date"]).date().isoformat()
    params = urllib.parse.urlencode(
        {
            "latitude": venue[0],
            "longitude": venue[1],
            "timezone": "auto",
            "start_date": day,
            "end_date": day,
            "daily": (
                "weather_code,temperature_2m_max,"
                "precipitation_probability_max,wind_speed_10m_max"
            ),
        }
    )
    try:
        daily = fetch_json(f"{OPEN_METEO}?{params}")["daily"]
        return {
            "rain_probability": daily["precipitation_probability_max"][0],
            "wind_max": daily["wind_speed_10m_max"][0],
            "temperature_max": daily["temperature_2m_max"][0],
        }
    except (OSError, KeyError, ValueError):
        return None


def weather_reason(data: dict[str, Any] | None) -> str | None:
    if not data:
        return None
    rain = int(data["rain_probability"])
    wind = round(float(data["wind_max"]))
    if rain >= 60:
        return f"Rain is likely ({rain}%), which adds uncertainty."
    if wind >= 35:
        return f"Strong winds around {wind} km/h may make scoring less predictable."
    if rain <= 20 and wind < 25:
        return "The forecast looks settled, so weather should have little influence."
    return None


def display_time(value: datetime) -> str:
    label = value.strftime("%a %I:%M %p").replace(" 0", " ")
    return label.replace(" AM", " am").replace(" PM", " pm")


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def win_rate(state: TeamState) -> float:
    return statistics.fmean(state.recent) if state.recent else 0.5


def predict(
    game: dict[str, Any],
    models: dict[str, Any],
    states: dict[str, TeamState],
    manual: dict[str, Any],
) -> dict[str, Any]:
    away_name, home_name = game["ateam"], game["hteam"]
    away = states.setdefault(away_name, TeamState())
    home = states.setdefault(home_name, TeamState())
    starts = game_time(game["date"])
    elo_home = 1 / (1 + 10 ** ((away.elo - home.elo - 45) / 400))
    model_home = float(models["home_probability"])
    home_probability = 0.78 * model_home + 0.22 * elo_home

    home_rest = (starts - home.last_game).days if home.last_game else 7
    away_rest = (starts - away.last_game).days if away.last_game else 7
    home_probability += clamp((home_rest - away_rest) * 0.006, -0.018, 0.018)

    verified = manual.get(str(game["id"]), {})
    home_probability += clamp(
        float(verified.get("home_probability_adjustment", 0)), -0.05, 0.05
    )
    home_probability = clamp(home_probability, 0.05, 0.95)
    pick_home = home_probability >= 0.5
    pick = home_name if pick_home else away_name
    pick_state, opponent_state = (home, away) if pick_home else (away, home)
    probability = home_probability if pick_home else 1 - home_probability
    majority = (
        models["home_tip_count"]
        if pick_home else models["model_count"] - models["home_tip_count"]
    )

    venue = VENUES.get(game["venue"])
    venue_coordinates = (venue[0], venue[1]) if venue else TEAM_HOME[home_name]
    travel = haversine_km(TEAM_HOME[away_name], venue_coordinates)
    weather = forecast(game)
    reasons = [f"{majority} of {models['model_count']} tracked models favour {pick}."]
    elo_gap = pick_state.elo - opponent_state.elo
    if elo_gap >= 45:
        reasons.append(f"{pick} also rates higher on results-based team strength.")
    elif elo_gap <= -45:
        opponent = away_name if pick_home else home_name
        reasons.append(f"{opponent} rates better historically, keeping this pick tighter.")
    form_gap = win_rate(pick_state) - win_rate(opponent_state)
    if form_gap >= 0.25:
        reasons.append(f"{pick} has the stronger recent five-game record.")
    elif form_gap <= -0.25:
        reasons.append("Recent form runs against the pick, so confidence is restrained.")
    if abs(home_rest - away_rest) >= 2:
        rested = home_name if home_rest > away_rest else away_name
        reasons.append(f"{rested} has the healthier turnaround between matches.")
    elif travel >= 2000 and pick_home:
        reasons.append(f"{away_name} also faces roughly {travel:,} km of travel.")
    weather_note = weather_reason(weather)
    if weather_note:
        reasons.append(weather_note)
    if verified.get("note"):
        reasons.append(str(verified["note"]))

    local = starts.astimezone(ADELAIDE)
    display_venue = venue[2] if venue else game["venue"]
    return {
        "id": int(game["id"]),
        "away_team": away_name,
        "home_team": home_name,
        "recommended_team": pick,
        "confidence_percent": round(probability * 100),
        "start_time": display_time(local),
        "venue": display_venue,
        "reason": " ".join(reasons[:3]),
        "context_reason": " ".join(reasons[1:3]),
        "model_count": int(models["model_count"]),
        "kickoff_epoch_millis": round(starts.timestamp() * 1000),
        "baseline_model_home_probability": round(model_home, 6),
        "context_home_probability": round(
            (home_probability - 0.78 * model_home) / 0.22, 6
        ),
        "metrics": {
            "model_home_probability": round(model_home, 4),
            "elo_home_probability": round(elo_home, 4),
            "final_home_probability": round(home_probability, 4),
            "home_elo": round(home.elo, 1),
            "away_elo": round(away.elo, 1),
            "home_recent_wins": sum(home.recent),
            "away_recent_wins": sum(away.recent),
            "home_rest_days": home_rest,
            "away_rest_days": away_rest,
            "away_travel_km": travel,
            "weather": weather,
        },
    }


def escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def render_kotlin(snapshot: dict[str, Any]) -> str:
    rows = []
    for tip in snapshot["tips"]:
        rows.append(
            "        Tip(\n"
            f"            id = {tip['id']},\n"
            f'            awayTeam = "{escape(tip["away_team"])}",\n'
            f'            homeTeam = "{escape(tip["home_team"])}",\n'
            f'            recommendedTeam = "{escape(tip["recommended_team"])}",\n'
            f"            confidencePercent = {tip['confidence_percent']},\n"
            f'            startTime = "{escape(tip["start_time"])}",\n'
            f'            venue = "{escape(tip["venue"])}",\n'
            f'            reason = "{escape(tip["reason"])}",\n'
            f"            modelCount = {tip['model_count']},\n"
            f"            kickoffEpochMillis = {tip['kickoff_epoch_millis']}L,\n"
            f"            baselineModelHomeProbability = {tip['baseline_model_home_probability']},\n"
            f"            contextHomeProbability = {tip['context_home_probability']},\n"
            "        ),"
        )
    return (
        "package com.langzonedev.rippertipper.data\n\n"
        "import com.langzonedev.rippertipper.model.Tip\n\n"
        "// Generated by backend/update_predictions.py. Do not edit by hand.\n"
        "object PredictionSnapshot {\n"
        f'    const val roundName = "{escape(snapshot["round_name"])}"\n'
        f'    const val roundDates = "{escape(snapshot["round_dates"])}"\n'
        f'    const val status = "{escape(snapshot["status"])}"\n'
        f'    const val updatedLabel = "{escape(snapshot["updated_label"])}"\n\n'
        "    val tips = listOf(\n"
        + "\n".join(rows)
        + "\n    )\n}\n"
    )


def main() -> None:
    now = datetime.now(timezone.utc)
    year = now.astimezone(ADELAIDE).year
    round_number, games = next_round(year)
    cutoff = game_time(games[0]["date"])
    states = build_states(completed_games(year - 4, year, cutoff))
    models = consensus(year, round_number)
    manual = json.loads(MANUAL_SIGNALS.read_text(encoding="utf-8")).get("games", {})
    tips = [
        predict(game, models[int(game["id"])], states, manual)
        for game in games if int(game["id"]) in models
    ]
    dates = [game_time(game["date"]).astimezone(ADELAIDE) for game in games]
    first_day, last_day = min(dates), max(dates)
    snapshot = {
        "round_name": f"Round {round_number}",
        "round_dates": (
            f"{first_day.day}–{last_day.day} {last_day.strftime('%B %Y')} · Adelaide time"
        ),
        "status": f"{max(tip['model_count'] for tip in tips)} models + match context",
        "updated_at": now.isoformat(),
        "updated_label": "Updated "
        + now.astimezone(ADELAIDE).strftime("%d %B, ").lstrip("0")
        + display_time(now.astimezone(ADELAIDE))[4:],
        "sources": ["Squiggle", "Open-Meteo"],
        "tips": tips,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    KOTLIN_OUTPUT.write_text(render_kotlin(snapshot), encoding="utf-8")
    print(f"Wrote {len(tips)} predictions for Round {round_number}")
    for tip in tips:
        print(
            f"{tip['away_team']} at {tip['home_team']}: "
            f"{tip['recommended_team']} {tip['confidence_percent']}%"
        )


if __name__ == "__main__":
    main()
