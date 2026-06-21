package com.langzonedev.rippertipper.model

enum class Confidence {
    HIGH,
    MEDIUM,
    LOW,
}

data class Tip(
    val id: Int,
    val awayTeam: String,
    val homeTeam: String,
    val recommendedTeam: String,
    val confidencePercent: Int,
    val startTime: String,
    val venue: String,
) {
    val confidence: Confidence
        get() = confidenceFor(confidencePercent)
}

fun confidenceFor(percent: Int): Confidence = when {
    percent >= 70 -> Confidence.HIGH
    percent >= 58 -> Confidence.MEDIUM
    else -> Confidence.LOW
}

