package com.langzonedev.rippertipper.data

import android.content.Context
import androidx.work.Constraints
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.Worker
import androidx.work.WorkerParameters
import androidx.work.WorkManager
import java.util.concurrent.TimeUnit

class LiveRefreshWorker(
    appContext: Context,
    workerParams: WorkerParameters,
) : Worker(appContext, workerParams) {
    override fun doWork(): Result {
        return try {
            LiveTipsRepository(applicationContext).refresh()
            schedule(applicationContext)
            Result.success()
        } catch (_: Exception) {
            Result.retry()
        }
    }

    companion object {
        private const val UNIQUE_WORK = "adaptive-live-tip-refresh"

        fun schedule(context: Context) {
            val now = System.currentTimeMillis()
            val nextKickoff = PredictionSnapshot.tips
                .map { it.kickoffEpochMillis }
                .filter { it > now }
                .minOrNull()
            val untilKickoff = nextKickoff?.minus(now) ?: TimeUnit.HOURS.toMillis(6)
            val delayMinutes = when {
                untilKickoff <= TimeUnit.HOURS.toMillis(24) -> 30L
                untilKickoff <= TimeUnit.HOURS.toMillis(72) -> 120L
                else -> 360L
            }
            val request = OneTimeWorkRequestBuilder<LiveRefreshWorker>()
                .setInitialDelay(delayMinutes, TimeUnit.MINUTES)
                .setConstraints(
                    Constraints.Builder()
                        .setRequiredNetworkType(NetworkType.CONNECTED)
                        .build(),
                )
                .build()
            WorkManager.getInstance(context).enqueueUniqueWork(
                UNIQUE_WORK,
                ExistingWorkPolicy.REPLACE,
                request,
            )
        }
    }
}
