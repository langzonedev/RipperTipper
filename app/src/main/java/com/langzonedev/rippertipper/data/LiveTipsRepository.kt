package com.langzonedev.rippertipper.data

import android.content.Context
import android.content.SharedPreferences
import com.langzonedev.rippertipper.model.Tip
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.time.Instant
import java.time.LocalDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import kotlin.math.roundToInt

data class LiveTipsResult(
    val tips: List<Tip>,
    val roundName: String,
    val roundDates: String,
    val status: String,
    val updatedLabel: String,
    val updatedAt: Long,
    val changedCount: Int,
)

class LiveTipsRepository(context: Context) {
    private val preferences = context.getSharedPreferences("live_tips", Context.MODE_PRIVATE)

    fun cached(): LiveTipsResult {
        val savedAt = preferences.getLong(KEY_UPDATED_AT, 0L)
        val cachedTips = applySavedPicks(PredictionSnapshot.tips)
        val changedCount = cachedTips.count(Tip::changed)
        return LiveTipsResult(
            tips = cachedTips,
            roundName = PredictionSnapshot.roundName,
            roundDates = PredictionSnapshot.roundDates,
            status = PredictionSnapshot.status,
            updatedLabel = if (savedAt > 0) freshnessLabel(savedAt) else PredictionSnapshot.updatedLabel,
            updatedAt = savedAt,
            changedCount = changedCount,
        )
    }

    fun refresh(): LiveTipsResult {
        return try {
            refreshHosted()
        } catch (_: Exception) {
            refreshFromSquiggle()
        }
    }

    private fun refreshHosted(): LiveTipsResult {
        var lastFailure: Exception? = null
        for (url in HOSTED_PREDICTION_URLS) {
            try {
                return refreshHosted(fetch(url))
            } catch (error: Exception) {
                lastFailure = error
            }
        }
        throw lastFailure ?: IllegalStateException("No hosted prediction URLs configured")
    }

    private fun refreshHosted(payload: JSONObject): LiveTipsResult {
        val tipsJson = payload.getJSONArray("tips")
        val editor = preferences.edit()
        val tips = mutableListOf<Tip>()
        for (index in 0 until tipsJson.length()) {
            val tip = hostedTip(tipsJson.getJSONObject(index), editor)
            tips.add(tip)
        }
        val now = System.currentTimeMillis()
        editor.putLong(KEY_UPDATED_AT, now).apply()
        return LiveTipsResult(
            tips = tips.sortedBy(Tip::kickoffEpochMillis),
            roundName = payload.getString("round_name"),
            roundDates = payload.getString("round_dates"),
            status = payload.optString("status", "Hosted prediction model"),
            updatedLabel = payload.optString("updated_label", "Updated just now"),
            updatedAt = parseHostedUpdatedAt(payload.optString("updated_at", "")) ?: now,
            changedCount = tips.count(Tip::changed),
        )
    }

    private fun refreshFromSquiggle(): LiveTipsResult {
        val target = findTargetRound()
        val tipsPayload = fetch(
            "https://api.squiggle.com.au/?q=tips;year=${target.year};round=${target.round}",
        )
        val byGame = groupTips(tipsPayload.getJSONArray("tips"))
        val gamesById = target.games.gamesById()
        val usesBakedRound = target.round == bakedRound() && target.year == bakedYear()
        val baselineTips = if (usesBakedRound) {
            PredictionSnapshot.tips
        } else {
            buildLiveRoundTips(target.games, byGame)
        }

        val editor = preferences.edit()
        val refreshed = baselineTips.map { baseline ->
            resultTip(baseline, gamesById[baseline.id])?.let { return@map it }
            refreshTip(baseline, byGame[baseline.id].orEmpty(), editor)
        }
        val now = System.currentTimeMillis()
        editor.putLong(KEY_UPDATED_AT, now).apply()
        return LiveTipsResult(
            tips = refreshed,
            roundName = "Round ${target.round}",
            roundDates = roundDates(target.games),
            status = if (usesBakedRound) PredictionSnapshot.status else "Live Squiggle consensus",
            updatedLabel = "Updated just now",
            updatedAt = now,
            changedCount = refreshed.count(Tip::changed),
        )
    }

    private fun hostedTip(row: JSONObject, editor: SharedPreferences.Editor): Tip {
        val recommended = row.getString("recommended_team")
        val gameId = row.getInt("id")
        val previous = preferences.getString(pickKey(gameId), recommended)
        val changed = previous != recommended
        editor.putString(pickKey(gameId), recommended)
        if (changed) editor.putBoolean(changedKey(gameId), true)

        return Tip(
            id = gameId,
            awayTeam = row.getString("away_team"),
            homeTeam = row.getString("home_team"),
            recommendedTeam = recommended,
            confidencePercent = row.getInt("confidence_percent"),
            startTime = row.getString("start_time"),
            venue = row.getString("venue"),
            reason = row.getString("reason"),
            modelCount = row.optInt("model_count", 0),
            kickoffEpochMillis = row.getLong("kickoff_epoch_millis"),
            baselineModelHomeProbability = row.optDouble("baseline_model_home_probability", 0.5),
            contextHomeProbability = row.optDouble("context_home_probability", 0.5),
            changed = changed || preferences.getBoolean(changedKey(gameId), false),
        )
    }

    private fun groupTips(tipsJson: JSONArray): Map<Int, List<JSONObject>> {
        val byGame = mutableMapOf<Int, MutableList<JSONObject>>()
        for (index in 0 until tipsJson.length()) {
            val tip = tipsJson.getJSONObject(index)
            if (!tip.isNull("tip") && !tip.isNull("confidence")) {
                byGame.getOrPut(tip.getInt("gameid")) { mutableListOf() }.add(tip)
            }
        }
        return byGame
    }

    private fun buildLiveRoundTips(
        games: JSONArray,
        byGame: Map<Int, List<JSONObject>>,
    ): List<Tip> {
        val rows = mutableListOf<Tip>()
        for (index in 0 until games.length()) {
            val game = games.getJSONObject(index)
            val models = byGame[game.getInt("id")].orEmpty()
            if (models.isEmpty()) continue

            val away = game.getString("ateam")
            val home = game.getString("hteam")
            val modelHome = homeProbabilities(models, home).average().coerceIn(0.05, 0.95)
            val recommended = if (modelHome >= 0.5) home else away
            val confidence = (if (modelHome >= 0.5) modelHome else 1.0 - modelHome)
                .times(100)
                .roundToInt()
            val modelVotes = models.count { it.getString("tip") == recommended }
            val kickoff = gameInstant(game.getString("date"))

            rows.add(
                Tip(
                    id = game.getInt("id"),
                    awayTeam = away,
                    homeTeam = home,
                    recommendedTeam = recommended,
                    confidencePercent = confidence,
                    startTime = displayTime(kickoff),
                    venue = displayVenue(game.getString("venue")),
                    reason = "$modelVotes of ${models.size} tracked models favour $recommended. Live round roll-over pick based on current Squiggle model consensus.",
                    modelCount = models.size,
                    kickoffEpochMillis = kickoff.toEpochMilli(),
                    baselineModelHomeProbability = modelHome,
                    contextHomeProbability = modelHome,
                ),
            )
        }
        return rows.sortedBy(Tip::kickoffEpochMillis)
    }

    private fun refreshTip(
        baseline: Tip,
        models: List<JSONObject>,
        editor: SharedPreferences.Editor,
    ): Tip {
        if (models.isEmpty()) return baseline

        val modelHome = homeProbabilities(models, baseline.homeTeam).average()
        val finalHome = (0.78 * modelHome + 0.22 * baseline.contextHomeProbability)
            .coerceIn(0.05, 0.95)
        val recommended = if (finalHome >= 0.5) baseline.homeTeam else baseline.awayTeam
        val confidence = (if (finalHome >= 0.5) finalHome else 1.0 - finalHome)
            .times(100)
            .roundToInt()
        val modelVotes = models.count { it.getString("tip") == recommended }
        val previous = preferences.getString(pickKey(baseline.id), baseline.recommendedTeam)
        val changed = previous != recommended
        editor.putString(pickKey(baseline.id), recommended)
        if (changed) editor.putBoolean(changedKey(baseline.id), true)

        val firstSentence =
            "$modelVotes of ${models.size} tracked models favour $recommended."
        val context = baseline.reason.substringAfter(". ", "")
        return baseline.copy(
            recommendedTeam = recommended,
            confidencePercent = confidence,
            modelCount = models.size,
            reason = if (context.isBlank()) firstSentence else "$firstSentence $context",
            changed = changed || preferences.getBoolean(changedKey(baseline.id), false),
        )
    }

    private fun homeProbabilities(models: List<JSONObject>, homeTeam: String): List<Double> {
        return models.map { model ->
            val confidence = model.getDouble("confidence") / 100.0
            if (model.getString("tip") == homeTeam) confidence else 1.0 - confidence
        }
    }

    private fun applySavedPicks(tips: List<Tip>): List<Tip> = tips.map { tip ->
        tip.copy(
            recommendedTeam = preferences.getString(pickKey(tip.id), tip.recommendedTeam)
                ?: tip.recommendedTeam,
            changed = preferences.getBoolean(changedKey(tip.id), false),
        )
    }

    private fun resultTip(tip: Tip, game: JSONObject?): Tip? {
        if (game == null || game.optInt("complete", 0) < 100) return null
        val awayScore = game.optInt("ascore")
        val homeScore = game.optInt("hscore")
        val winner = when {
            homeScore > awayScore -> tip.homeTeam
            awayScore > homeScore -> tip.awayTeam
            else -> "Draw"
        }
        return tip.copy(
            recommendedTeam = winner,
            confidencePercent = 100,
            reason = if (winner == "Draw") {
                "Final result: ${tip.awayTeam} $awayScore, ${tip.homeTeam} $homeScore."
            } else {
                "$winner won. Final result: ${tip.awayTeam} $awayScore, ${tip.homeTeam} $homeScore."
            },
            changed = false,
            resultWinner = winner,
            resultLabel = "${tip.awayTeam} $awayScore  ·  ${tip.homeTeam} $homeScore",
        )
    }

    private fun findTargetRound(): TargetRound {
        val currentYear = Instant.now().atZone(ADELAIDE).year
        val thisYear = targetRoundForYear(currentYear)
        if (thisYear.games.length() > 0) return thisYear
        return targetRoundForYear(currentYear + 1)
    }

    private fun targetRoundForYear(year: Int): TargetRound {
        val games = fetch("https://api.squiggle.com.au/?q=games;year=$year")
            .getJSONArray("games")
        val now = Instant.now()
        val eligible = mutableListOf<JSONObject>()
        for (index in 0 until games.length()) {
            val game = games.getJSONObject(index)
            if (game.isNull("ateam") || game.isNull("hteam")) continue
            val starts = gameInstant(game.getString("date"))
            val complete = game.optInt("complete", 0) >= 100
            val nearOrFuture = starts.plusSeconds(6 * 60 * 60) >= now
            if (!complete && nearOrFuture) eligible.add(game)
        }
        if (eligible.isEmpty()) return TargetRound(year, 0, JSONArray())

        val round = eligible.minOf { it.getInt("round") }
        val selected = (0 until games.length())
            .map { games.getJSONObject(it) }
            .filter {
                !it.isNull("ateam") &&
                    !it.isNull("hteam") &&
                    it.getInt("round") == round
            }
            .sortedBy { gameInstant(it.getString("date")) }
        return TargetRound(year, round, JSONArray(selected))
    }

    private fun roundDates(games: JSONArray): String {
        val dates = (0 until games.length()).map {
            gameInstant(games.getJSONObject(it).getString("date"))
                .atZone(ADELAIDE)
                .toLocalDate()
        }
        val first = dates.minOrNull() ?: return PredictionSnapshot.roundDates
        val last = dates.maxOrNull() ?: first
        val monthFormatter = DateTimeFormatter.ofPattern("MMMM yyyy")
        return if (first.month == last.month && first.year == last.year) {
            "${first.dayOfMonth}–${last.dayOfMonth} ${last.format(monthFormatter)} · Adelaide time"
        } else {
            "${first.dayOfMonth} ${first.format(monthFormatter)}–${last.dayOfMonth} ${last.format(monthFormatter)} · Adelaide time"
        }
    }

    private fun displayVenue(venue: String): String = when (venue) {
        "Carrara" -> "People First Stadium"
        "Docklands" -> "Marvel Stadium"
        "Kardinia Park" -> "GMHBA Stadium"
        "M.C.G." -> "MCG"
        "Perth Stadium" -> "Optus Stadium"
        "S.C.G." -> "SCG"
        "Sydney Showground" -> "ENGIE Stadium"
        "York Park" -> "UTAS Stadium"
        else -> venue
    }

    private fun displayTime(value: Instant): String {
        return value.atZone(ADELAIDE)
            .format(DateTimeFormatter.ofPattern("EEE h:mm a"))
            .replace("AM", "am")
            .replace("PM", "pm")
    }

    private fun gameInstant(value: String): Instant {
        return LocalDateTime.parse(value, GAME_TIME_FORMATTER)
            .atZone(MELBOURNE)
            .toInstant()
    }

    private fun JSONArray.gamesById(): Map<Int, JSONObject> {
        val result = mutableMapOf<Int, JSONObject>()
        for (index in 0 until length()) {
            val game = getJSONObject(index)
            result[game.getInt("id")] = game
        }
        return result
    }

    private fun bakedRound() = PredictionSnapshot.roundName.substringAfter("Round ").toInt()

    private fun bakedYear() = Instant.ofEpochMilli(PredictionSnapshot.tips.first().kickoffEpochMillis)
        .atZone(ADELAIDE)
        .year

    private fun fetch(url: String): JSONObject {
        val connection = URL(url).openConnection() as HttpURLConnection
        return try {
            connection.connectTimeout = 15_000
            connection.readTimeout = 15_000
            connection.setRequestProperty(
                "User-Agent",
                "RipperTipper/0.5 (contact: 202942822+langzonedev@users.noreply.github.com)",
            )
            connection.inputStream.bufferedReader().use { JSONObject(it.readText()) }
        } finally {
            connection.disconnect()
        }
    }

    private fun parseHostedUpdatedAt(value: String): Long? {
        return try {
            Instant.parse(value).toEpochMilli()
        } catch (_: Exception) {
            null
        }
    }

    companion object {
        private val HOSTED_PREDICTION_URLS = listOf(
            "https://langzonedev.github.io/RipperTipper/current_round.json",
            "https://raw.githubusercontent.com/langzonedev/RipperTipper/main/public/current_round.json",
        )
        private val ADELAIDE: ZoneId = ZoneId.of("Australia/Adelaide")
        private val MELBOURNE: ZoneId = ZoneId.of("Australia/Melbourne")
        private val GAME_TIME_FORMATTER: DateTimeFormatter =
            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")
        private const val KEY_UPDATED_AT = "updated_at"

        private fun pickKey(gameId: Int) = "pick_$gameId"
        private fun changedKey(gameId: Int) = "changed_$gameId"

        fun freshnessLabel(timestamp: Long, now: Long = System.currentTimeMillis()): String {
            val minutes = ((now - timestamp).coerceAtLeast(0) / 60_000).toInt()
            return when {
                minutes < 1 -> "Updated just now"
                minutes == 1 -> "Updated 1 minute ago"
                minutes < 60 -> "Updated $minutes minutes ago"
                else -> {
                    val formatter = DateTimeFormatter.ofPattern("d MMM, h:mm a")
                    "Updated " + Instant.ofEpochMilli(timestamp)
                        .atZone(ADELAIDE)
                        .format(formatter)
                        .lowercase()
                }
            }
        }
    }
}

private data class TargetRound(
    val year: Int,
    val round: Int,
    val games: JSONArray,
)
