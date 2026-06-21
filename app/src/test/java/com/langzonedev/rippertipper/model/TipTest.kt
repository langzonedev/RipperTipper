package com.langzonedev.rippertipper.model

import com.langzonedev.rippertipper.data.SampleTips
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
    fun `round 16 snapshot has seven unique fixtures`() {
        assertEquals(7, SampleTips.round.size)
        assertEquals(7, SampleTips.round.map(Tip::id).toSet().size)
    }
}
