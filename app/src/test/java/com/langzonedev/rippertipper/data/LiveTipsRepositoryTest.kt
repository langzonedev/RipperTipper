package com.langzonedev.rippertipper.data

import org.junit.Assert.assertEquals
import org.junit.Test

class LiveTipsRepositoryTest {
    @Test
    fun `freshness label reports recent updates plainly`() {
        val now = 1_000_000L
        assertEquals("Updated just now", LiveTipsRepository.freshnessLabel(now, now))
        assertEquals(
            "Updated 5 minutes ago",
            LiveTipsRepository.freshnessLabel(now - 300_000L, now),
        )
    }
}
