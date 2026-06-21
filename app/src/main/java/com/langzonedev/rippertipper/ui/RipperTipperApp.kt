package com.langzonedev.rippertipper.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.langzonedev.rippertipper.data.PredictionSnapshot
import com.langzonedev.rippertipper.model.Confidence
import com.langzonedev.rippertipper.model.Tip
import com.langzonedev.rippertipper.ui.theme.Caution
import com.langzonedev.rippertipper.ui.theme.Forest
import com.langzonedev.rippertipper.ui.theme.ForestSoft
import com.langzonedev.rippertipper.ui.theme.Gold
import com.langzonedev.rippertipper.ui.theme.InkMuted
import com.langzonedev.rippertipper.ui.theme.RipperTipperTheme
import com.langzonedev.rippertipper.ui.theme.Success

@Composable
fun RipperTipperApp() {
    var expandedTipId by remember { mutableIntStateOf(-1) }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .navigationBarsPadding(),
    ) {
        item {
            Hero()
        }
        item {
            RoundSummary()
        }
        items(PredictionSnapshot.tips, key = Tip::id) { tip ->
            TipCard(
                tip = tip,
                expanded = tip.id == expandedTipId,
                onClick = {
                    expandedTipId = if (tip.id == expandedTipId) -1 else tip.id
                },
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 6.dp),
            )
        }
        item {
            Text(
                text = PredictionSnapshot.updatedLabel,
                style = MaterialTheme.typography.bodyMedium,
                color = InkMuted,
                textAlign = TextAlign.Center,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(24.dp),
            )
        }
    }
}

@Composable
private fun Hero() {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(Forest)
            .statusBarsPadding()
            .padding(horizontal = 20.dp, vertical = 24.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .clip(RoundedCornerShape(10.dp))
                    .background(Gold)
                    .width(42.dp)
                    .height(42.dp),
            ) {
                Text(
                    text = "RT",
                    color = Forest,
                    fontWeight = FontWeight.Black,
                    fontSize = 16.sp,
                )
            }
            Spacer(Modifier.width(12.dp))
            Text(
                text = "RIPPER TIPPER",
                color = Color.White,
                style = MaterialTheme.typography.titleMedium,
                letterSpacing = 1.6.sp,
            )
        }

        Spacer(Modifier.height(30.dp))

        Text(
            text = "NEXT UP  ·  ${PredictionSnapshot.roundName.uppercase()}",
            color = Gold,
            style = MaterialTheme.typography.labelLarge,
        )
        Text(
            text = "Here’s who\nto pick.",
            color = Color.White,
            style = MaterialTheme.typography.displaySmall,
        )
        Spacer(Modifier.height(12.dp))
        Text(
            text = PredictionSnapshot.roundDates,
            color = Color.White.copy(alpha = 0.68f),
            style = MaterialTheme.typography.bodyLarge,
        )
    }
}

@Composable
private fun RoundSummary() {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 20.dp, vertical = 18.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column {
            Text(
                text = "${PredictionSnapshot.tips.size} PICKS READY",
                style = MaterialTheme.typography.labelLarge,
                color = Forest,
            )
            Text(
                text = PredictionSnapshot.status,
                style = MaterialTheme.typography.bodyMedium,
                color = InkMuted,
            )
        }
        Surface(
            color = Success.copy(alpha = 0.12f),
            shape = CircleShape,
        ) {
            Text(
                text = "● LIVE",
                color = Success,
                style = MaterialTheme.typography.labelLarge,
                modifier = Modifier.padding(horizontal = 12.dp, vertical = 7.dp),
            )
        }
    }
}

@Composable
private fun TipCard(
    tip: Tip,
    expanded: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Card(
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(
                    text = "${tip.startTime}  ·  ${tip.venue}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = InkMuted,
                )
                Text(
                    text = if (expanded) "−" else "+",
                    style = MaterialTheme.typography.titleLarge,
                    color = ForestSoft,
                )
            }

            Spacer(Modifier.height(14.dp))

            Text(
                text = "PICK",
                style = MaterialTheme.typography.labelLarge,
                color = InkMuted,
            )
            Text(
                text = tip.recommendedTeam,
                style = MaterialTheme.typography.headlineSmall,
                color = Forest,
            )

            Spacer(Modifier.height(14.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = "${tip.awayTeam}  vs  ${tip.homeTeam}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = InkMuted,
                    modifier = Modifier.weight(1f),
                )
                ConfidencePill(tip)
            }

            AnimatedVisibility(visible = expanded) {
                Column {
                    HorizontalDivider(
                        modifier = Modifier.padding(vertical = 16.dp),
                        color = MaterialTheme.colorScheme.outline,
                    )
                    Text(
                        text = "Why this pick",
                        style = MaterialTheme.typography.titleMedium,
                    )
                    Spacer(Modifier.height(5.dp))
                    Text(
                        text = tip.reason,
                        style = MaterialTheme.typography.bodyMedium,
                        color = InkMuted,
                    )
                }
            }
        }
    }
}

@Composable
private fun ConfidencePill(tip: Tip) {
    val (label, colour) = when (tip.confidence) {
        Confidence.HIGH -> "HIGH" to Success
        Confidence.MEDIUM -> "MEDIUM" to Caution
        Confidence.LOW -> "CLOSE" to InkMuted
    }
    Surface(
        color = colour.copy(alpha = 0.12f),
        shape = CircleShape,
    ) {
        Text(
            text = "${tip.confidencePercent}%  $label",
            color = colour,
            style = MaterialTheme.typography.labelLarge,
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
        )
    }
}

@Preview(showBackground = true, widthDp = 393, heightDp = 852)
@Composable
private fun RipperTipperPreview() {
    RipperTipperTheme {
        RipperTipperApp()
    }
}
