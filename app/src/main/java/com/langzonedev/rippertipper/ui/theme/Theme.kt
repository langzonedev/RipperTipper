package com.langzonedev.rippertipper.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val RipperColors = lightColorScheme(
    primary = Forest,
    onPrimary = Color.White,
    secondary = Gold,
    onSecondary = Forest,
    background = Cream,
    onBackground = Forest,
    surface = Paper,
    onSurface = Forest,
    surfaceVariant = Color(0xFFE9EDE7),
    onSurfaceVariant = InkMuted,
    outline = Border,
)

@Composable
fun RipperTipperTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = RipperColors,
        typography = RipperTypography,
        content = content,
    )
}

