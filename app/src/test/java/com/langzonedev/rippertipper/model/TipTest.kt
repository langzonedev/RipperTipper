package com.langzonedev.rippertipper.model

import com.langzonedev.rippertipper.data.PredictionSnapshot
import org.junit.Assert.assertEquals
import org.junit.Test

class TipTest {
    @Test
    fun `confidence thresholds are stable`() {
        assertEquals(Confidence.HIGH, confidenceFor(70))
        assertEquals(Confidence.MEDIUM, confidenceFor(69))
        assertEquals(Confidence.MEDIUM, confidenceFor(58))
        assertEquals(Confidence.LOW, confidenceFor(57))
    }

    @Test
    fun `snapshot has unique fixtures`() {
        assertEquals(PredictionSnapshot.tips.size, PredictionSnapshot.tips.map(Tip::id).toSet().size)
    }
}
