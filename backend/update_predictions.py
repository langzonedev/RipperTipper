"""Build the current Ripper Tipper snapshot from free data sources."""

from __future__ import annotations

import json
import math
import re
import statistics
import urllib.parse
import urllib.request
import html as html_lib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
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
AFL_INJURY_LIST = "https://www.afl.com.au/matches/injury-list"
USER_AGENT = (
    "RipperTipper/0.4 "
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
    recent_margins: list[int] = field(default_factory=list)
    recent_scores_for: list[int] = field(default_factory=list)
    recent_scores_against: list[int] = field(default_factory=list)
    last_game: datetime | None = None
    venue_results: dict[str, list[int]] = field(default_factory=dict)


@dataclass
class AvailabilitySignal:
    burden: float = 0.0
    tests: int = 0
    long_term: int = 0
    mix_score: float = 0.0
    note: str | None = None


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = " ".join(data.replace("\xa0", " ").split())
        if value:
            self.parts.append(value)


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
        home_margin = int(game["hscore"]) - int(game["ascore"])
        away_margin = -home_margin
        home.recent_margins = (home.recent_margins + [home_margin])[-5:]
        away.recent_margins = (away.recent_margins + [away_margin])[-5:]
        home.recent_scores_for = (home.recent_scores_for + [int(game["hscore"])])[-5:]
        home.recent_scores_against = (
            home.recent_scores_against + [int(game["ascore"])]
        )[-5:]
        away.recent_scores_for = (away.recent_scores_for + [int(game["ascore"])])[-5:]
        away.recent_scores_against = (
            away.recent_scores_against + [int(game["hscore"])]
        )[-5:]
        venue = str(game.get("venue", ""))
        if venue:
            home.venue_results[venue] = (home.venue_results.get(venue, []) + [int(actual_home == 1)])[-8:]
            away.venue_results[venue] = (away.venue_results.get(venue, []) + [int(actual_home == 0)])[-8:]
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


def power_rankings(year: int, round_number: int) -> dict[str, float]:
    try:
        rows = squiggle(f"q=power;year={year};round={max(round_number - 1, -1)}")["power"]
    except (OSError, KeyError, ValueError):
        return {}

    grouped: dict[str, list[float]] = {}
    for row in rows:
        if int(row.get("dummy", 0)):
            continue
        try:
            grouped.setdefault(str(row["team"]), []).append(float(row["power"]))
        except (KeyError, TypeError, ValueError):
            continue
    return {team: statistics.fmean(values) for team, values in grouped.items() if values}


def return_weight(value: str) -> float:
    value = value.lower()
    if "season" in value or "indefinite" in value:
        return 1.25
    if "tbc" in value or "tba" in value:
        return 1.0
    if "test" in value:
        return 0.35
    if "managed" in value:
        return 0.45
    if "round" in value or "suspension" in value:
        return 0.75
    weeks = [int(number) for number in re.findall(r"\d+", value)]
    if not weeks:
        return 0.65
    longest = max(weeks)
    if longest <= 1:
        return 0.5
    if longest <= 3:
        return 0.75
    if longest <= 6:
        return 1.0
    return 1.2


def injury_row_return(row: str) -> str:
    patterns = [
        r"(Season)$",
        r"(Indefinite)$",
        r"(TBC|TBA)$",
        r"(Test)$",
        r"(Managed)$",
        r"(Round\s+\d+)$",
        r"(\d+(?:-\d+)?\s+weeks?)$",
        r"(\d+\s+week)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, row, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return row


def mix_score(text: str) -> float:
    lowered = text.lower()
    positive = sum(
        lowered.count(term)
        for term in [
            "available",
            "return",
            "returns",
            "back from injury",
            "unchanged",
            "boost",
            "cleared",
            "on track",
        ]
    )
    negative = sum(
        lowered.count(term)
        for term in [
            "ruled out",
            "will miss",
            "sidelined",
            "injury",
            "injured",
            "hamstring",
            "concussion",
            "fitness test",
            "managed",
        ]
    )
    return clamp((positive - negative) * 0.2, -1.0, 1.0)


def extract_injury_signals() -> dict[str, AvailabilitySignal]:
    team_order = [
        "Adelaide",
        "Brisbane Lions",
        "Carlton",
        "Collingwood",
        "Essendon",
        "Fremantle",
        "Geelong",
        "Gold Coast",
        "Greater Western Sydney",
        "Hawthorn",
        "Melbourne",
        "North Melbourne",
        "Port Adelaide",
        "Richmond",
        "St Kilda",
        "Sydney",
        "West Coast",
        "Western Bulldogs",
    ]
    try:
        html = fetch_json_text(AFL_INJURY_LIST)
    except OSError:
        return {}

    signals: dict[str, AvailabilitySignal] = {}
    start = html.find("Check out the injury updates from all 18 clubs")
    body = html[start if start >= 0 else 0 :]
    tables = list(re.finditer(r"<table\b.*?</table>", body, flags=re.IGNORECASE | re.DOTALL))
    for team, match in zip(team_order, tables):
        table = match.group(0)
        rows = []
        for row in re.findall(r"<tr\b.*?</tr>", table, flags=re.IGNORECASE | re.DOTALL):
            cells = re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", row, flags=re.IGNORECASE | re.DOTALL)
            clean_cells = [clean_html(cell) for cell in cells]
            if len(clean_cells) == 3 and clean_cells[0].lower() != "player":
                rows.append(clean_cells)

        next_start = match.end()
        next_table = body.find("<table", next_start)
        section = body[next_start : next_table if next_table >= 0 else len(body)]
        note = clean_html(section)
        weights = [return_weight(row[2]) for row in rows]
        signals[team] = AvailabilitySignal(
            burden=round(sum(weights), 2),
            tests=sum(1 for row in rows if "test" in row[2].lower()),
            long_term=sum(1 for row in rows if return_weight(row[2]) >= 1.0),
            mix_score=mix_score(note),
            note=note[:220] if note else None,
        )
    return signals


def fetch_json_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def clean_html(value: str) -> str:
    value = re.sub(r"<script\b.*?</script>", " ", value, flags=re.IGNORECASE | re.DOTALL)
    value = re.sub(r"<style\b.*?</style>", " ", value, flags=re.IGNORECASE | re.DOTALL)
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(html_lib.unescape(value).replace("\xa0", " ").split())


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


def mean(values: list[int] | list[float], default: float = 0.0) -> float:
    return statistics.fmean(values) if values else default


def venue_rate(state: TeamState, venue: str) -> float:
    return mean(state.venue_results.get(venue, []), 0.5)


def availability_adjustment(
    home_signal: AvailabilitySignal,
    away_signal: AvailabilitySignal,
) -> float:
    injury_component = (away_signal.burden - home_signal.burden) * 0.004
    mix_component = (home_signal.mix_score - away_signal.mix_score) * 0.012
    return clamp(injury_component + mix_component, -0.04, 0.04)


def upset_drag(
    probability: float,
    models: dict[str, Any],
    weather: dict[str, Any] | None,
    form_runs_against_pick: bool,
) -> float:
    risk = 0.0
    if 0.55 <= probability <= 0.72:
        risk += 0.012
    model_count = max(int(models["model_count"]), 1)
    favourite_votes = max(
        int(models["home_tip_count"]),
        model_count - int(models["home_tip_count"]),
    )
    if favourite_votes / model_count < 0.72:
        risk += 0.015
    if weather:
        if int(weather.get("rain_probability", 0)) >= 55:
            risk += 0.012
        if float(weather.get("wind_max", 0)) >= 32:
            risk += 0.010
    if form_runs_against_pick:
        risk += 0.014
    return clamp(risk, 0.0, 0.045)


def apply_drag_to_home_probability(
    home_probability: float,
    risk: float,
) -> float:
    if risk <= 0:
        return home_probability
    direction = 1 if home_probability >= 0.5 else -1
    return home_probability - direction * min(abs(home_probability - 0.5), risk)


def predict(
    game: dict[str, Any],
    models: dict[str, Any],
    states: dict[str, TeamState],
    powers: dict[str, float],
    availability: dict[str, AvailabilitySignal],
    manual: dict[str, Any],
) -> dict[str, Any]:
    away_name, home_name = game["ateam"], game["hteam"]
    away = states.setdefault(away_name, TeamState())
    home = states.setdefault(home_name, TeamState())
    starts = game_time(game["date"])
    elo_home = 1 / (1 + 10 ** ((away.elo - home.elo - 45) / 400))
    model_home = float(models["home_probability"])
    home_probability = 0.72 * model_home + 0.20 * elo_home

    home_rest = (starts - home.last_game).days if home.last_game else 7
    away_rest = (starts - away.last_game).days if away.last_game else 7
    home_probability += clamp((home_rest - away_rest) * 0.006, -0.018, 0.018)

    power_home = powers.get(home_name)
    power_away = powers.get(away_name)
    power_adjustment = 0.0
    if power_home is not None and power_away is not None:
        power_adjustment = clamp((power_home - power_away) * 0.003, -0.04, 0.04)
        home_probability += power_adjustment

    margin_adjustment = clamp(
        (mean(home.recent_margins) - mean(away.recent_margins)) * 0.0012,
        -0.035,
        0.035,
    )
    home_probability += margin_adjustment

    venue = VENUES.get(game["venue"])
    display_venue = venue[2] if venue else game["venue"]
    venue_adjustment = clamp((venue_rate(home, game["venue"]) - 0.5) * 0.025, -0.018, 0.018)
    home_probability += venue_adjustment

    home_signal = availability.get(home_name, AvailabilitySignal())
    away_signal = availability.get(away_name, AvailabilitySignal())
    availability_delta = availability_adjustment(home_signal, away_signal)
    home_probability += availability_delta

    weather = forecast(game)
    form_gap_for_home = win_rate(home) - win_rate(away)
    provisional_pick_home = home_probability >= 0.5
    form_runs_against_pick = (
        form_gap_for_home <= -0.25 if provisional_pick_home else form_gap_for_home >= 0.25
    )
    upset_risk = upset_drag(
        max(home_probability, 1 - home_probability),
        models,
        weather,
        form_runs_against_pick,
    )
    home_probability = apply_drag_to_home_probability(home_probability, upset_risk)

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

    venue_coordinates = (venue[0], venue[1]) if venue else TEAM_HOME[home_name]
    travel = haversine_km(TEAM_HOME[away_name], venue_coordinates)
    reasons = [f"{majority} of {models['model_count']} tracked models favour {pick}."]
    if upset_risk >= 0.03:
        reasons.append("Upset-risk flags are active, so confidence has been trimmed.")
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
    margin_gap = mean(pick_state.recent_margins) - mean(opponent_state.recent_margins)
    if margin_gap >= 18:
        reasons.append(f"{pick}'s recent scoring margins are materially stronger.")
    elif margin_gap <= -18:
        reasons.append("Recent margins warn this favourite may be more fragile.")
    pick_signal, opponent_signal = (
        (home_signal, away_signal) if pick_home else (away_signal, home_signal)
    )
    if opponent_signal.burden - pick_signal.burden >= 2.0:
        reasons.append(f"{pick} has the cleaner current availability profile.")
    elif pick_signal.burden - opponent_signal.burden >= 2.0:
        reasons.append("Injury-list pressure keeps this pick tighter than the market.")
    if abs(power_adjustment) >= 0.018:
        power_side = home_name if power_adjustment > 0 else away_name
        reasons.append(f"Squiggle power rankings also lean toward {power_side}.")
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
            "power_home": round(power_home, 2) if power_home is not None else None,
            "power_away": round(power_away, 2) if power_away is not None else None,
            "power_adjustment": round(power_adjustment, 4),
            "margin_adjustment": round(margin_adjustment, 4),
            "venue_adjustment": round(venue_adjustment, 4),
            "availability_adjustment": round(availability_delta, 4),
            "upset_risk_drag": round(upset_risk, 4),
            "home_availability_burden": home_signal.burden,
            "away_availability_burden": away_signal.burden,
            "home_elo": round(home.elo, 1),
            "away_elo": round(away.elo, 1),
            "home_recent_wins": sum(home.recent),
            "away_recent_wins": sum(away.recent),
            "home_recent_margin": round(mean(home.recent_margins), 1),
            "away_recent_margin": round(mean(away.recent_margins), 1),
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
    powers = power_rankings(year, round_number)
    availability = extract_injury_signals()
    manual = json.loads(MANUAL_SIGNALS.read_text(encoding="utf-8")).get("games", {})
    tips = [
        predict(game, models[int(game["id"])], states, powers, availability, manual)
        for game in games if int(game["id"]) in models
    ]
    dates = [game_time(game["date"]).astimezone(ADELAIDE) for game in games]
    first_day, last_day = min(dates), max(dates)
    snapshot = {
        "round_name": f"Round {round_number}",
        "round_dates": (
            f"{first_day.day}–{last_day.day} {last_day.strftime('%B %Y')} · Adelaide time"
        ),
        "status": f"{max(tip['model_count'] for tip in tips)} models + injury/form context",
        "updated_at": now.isoformat(),
        "updated_label": "Updated "
        + now.astimezone(ADELAIDE).strftime("%d %B, ").lstrip("0")
        + display_time(now.astimezone(ADELAIDE))[4:],
        "sources": ["Squiggle", "Open-Meteo", "AFL injury list"],
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

