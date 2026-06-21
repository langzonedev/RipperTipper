package com.langzonedev.rippertipper.data

import com.langzonedev.rippertipper.model.Tip

object SampleTips {
    const val roundName = "Round 16"
    const val roundDates = "25–28 June 2026 · Adelaide time"

    val round = listOf(
        Tip(1, "Sydney", "Brisbane Lions", "Brisbane Lions", 56, "Thu 7:00 pm", "Gabba"),
        Tip(2, "Greater Western Sydney", "Hawthorn", "Hawthorn", 73, "Fri 7:10 pm", "MCG"),
        Tip(3, "West Coast", "Carlton", "Carlton", 83, "Sat 12:45 pm", "Marvel Stadium"),
        Tip(4, "Richmond", "Collingwood", "Collingwood", 85, "Sat 3:45 pm", "MCG"),
        Tip(5, "Adelaide", "Port Adelaide", "Adelaide", 68, "Sat 7:05 pm", "Adelaide Oval"),
        Tip(6, "Essendon", "North Melbourne", "North Melbourne", 66, "Sun 2:45 pm", "Marvel Stadium"),
        Tip(7, "Gold Coast", "Fremantle", "Fremantle", 76, "Sun 4:40 pm", "Optus Stadium"),
    )
}
