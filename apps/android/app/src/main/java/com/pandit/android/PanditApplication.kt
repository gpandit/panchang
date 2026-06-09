package com.pandit.android

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class PanditApplication : Application() {

    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(
                NotificationChannel(
                    CHANNEL_REMINDERS,
                    getString(R.string.notif_channel_reminders_name),
                    NotificationManager.IMPORTANCE_DEFAULT
                ).apply { description = getString(R.string.notif_channel_reminders_desc) }
            )
            manager.createNotificationChannel(
                NotificationChannel(
                    CHANNEL_DAILY,
                    getString(R.string.notif_channel_daily_name),
                    NotificationManager.IMPORTANCE_LOW
                ).apply { description = getString(R.string.notif_channel_daily_desc) }
            )
        }
    }

    companion object {
        const val CHANNEL_REMINDERS = "pandit_reminders"
        const val CHANNEL_DAILY = "pandit_daily"
    }
}
