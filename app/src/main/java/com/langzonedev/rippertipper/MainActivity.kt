package com.langzonedev.rippertipper

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.langzonedev.rippertipper.ui.RipperTipperApp
import com.langzonedev.rippertipper.ui.theme.RipperTipperTheme
import com.langzonedev.rippertipper.data.LiveRefreshWorker

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.dark(android.graphics.Color.TRANSPARENT),
            navigationBarStyle = SystemBarStyle.light(
                android.graphics.Color.TRANSPARENT,
                android.graphics.Color.TRANSPARENT,
            ),
        )
        LiveRefreshWorker.schedule(this)
        setContent {
            RipperTipperTheme {
                RipperTipperApp()
            }
        }
    }
}
