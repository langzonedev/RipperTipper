package com.langzonedev.rippertipper.model

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
}

