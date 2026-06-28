package com.langzonedev.rippertipper.data

import android.content.Context
import com.langzonedev.rippertipper.model.Tip
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import kotlin.math.roundToInt

data class LiveTipsResult(
    val tips: List<Tip>,
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
            updatedLabel = if (savedAt > 0) freshnessLabel(savedAt) else PredictionSnapshot.updatedLabel,
            updatedAt = savedAt,
            changedCount = changedCount,
        )
    }

    fun refresh(): LiveTipsResult {
        val round = PredictionSnapshot.roundName.substringAfter("Round ").toInt()
        val year = Instant.ofEpochMilli(PredictionSnapshot.tips.first().kickoffEpochMillis)
            .atZone(ZoneId.of("Australia/Adelaide"))
            .year
        val payload = fetch(
            "https://api.squiggle.com.au/?q=tips;year=$year;round=$round",
        )
        val gamesPayload = fetch(
            "https://api.squiggle.com.au/?q=games;year=$year;round=$round",
        )
        val tipsJson = payload.getJSONArray("tips")
        val gamesJson = gamesPayload.getJSONArray("games")
        val byGame = mutableMapOf<Int, MutableList<JSONObject>>()
        for (index in 0 until tipsJson.length()) {
            val tip = tipsJson.getJSONObject(index)
            if (!tip.isNull("tip") && !tip.isNull("confidence")) {
                byGame.getOrPut(tip.getInt("gameid")) { mutableListOf() }.add(tip)
            }
        }
        val gamesById = mutableMapOf<Int, JSONObject>()
        for (index in 0 until gamesJson.length()) {
            val game = gamesJson.getJSONObject(index)
            gamesById[game.getInt("id")] = game
        }

        val editor = preferences.edit()
        val refreshed = PredictionSnapshot.tips.map { baseline ->
            resultTip(baseline, gamesById[baseline.id])?.let { return@map it }
            val models = byGame[baseline.id].orEmpty()
            if (models.isEmpty()) return@map baseline

            val homeProbabilities = models.map { model ->
                val confidence = model.getDouble("confidence") / 100.0
                if (model.getString("tip") == baseline.homeTeam) confidence else 1.0 - confidence
            }
            val modelHome = homeProbabilities.average()
            val finalHome = (0.78 * modelHome + 0.22 * baseline.contextHomeProbability)
                .coerceIn(0.05, 0.95)
            val recommended = if (finalHome >= 0.5) baseline.homeTeam else baseline.awayTeam
            val confidence = (
                if (finalHome >= 0.5) finalHome else 1.0 - finalHome
                ).times(100).roundToInt()
            val modelVotes = models.count { it.getString("tip") == recommended }
            val previous = preferences.getString(pickKey(baseline.id), baseline.recommendedTeam)
            val changed = previous != recommended
            editor.putString(pickKey(baseline.id), recommended)
            if (changed) editor.putBoolean(changedKey(baseline.id), true)

            val firstSentence =
                "$modelVotes of ${models.size} tracked models favour $recommended."
            val context = baseline.reason.substringAfter(". ", "")
            baseline.copy(
                recommendedTeam = recommended,
                confidencePercent = confidence,
                modelCount = models.size,
                reason = if (context.isBlank()) firstSentence else "$firstSentence $context",
                changed = changed || preferences.getBoolean(changedKey(baseline.id), false),
            )
        }
        val now = System.currentTimeMillis()
        editor.putLong(KEY_UPDATED_AT, now).apply()
        return LiveTipsResult(
            tips = refreshed,
            updatedLabel = "Updated just now",
            updatedAt = now,
            changedCount = refreshed.count(Tip::changed),
        )
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

    private fun fetch(url: String): JSONObject {
        val connection = URL(url).openConnection() as HttpURLConnection
        return try {
            connection.connectTimeout = 15_000
            connection.readTimeout = 15_000
            connection.setRequestProperty(
                "User-Agent",
                "RipperTipper/0.3 (contact: 202942822+langzonedev@users.noreply.github.com)",
            )
            connection.inputStream.bufferedReader().use { JSONObject(it.readText()) }
        } finally {
            connection.disconnect()
        }
    }

    companion object {
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
                        .atZone(ZoneId.of("Australia/Adelaide"))
                        .format(formatter)
                        .lowercase()
                }
            }
        }
    }
}
