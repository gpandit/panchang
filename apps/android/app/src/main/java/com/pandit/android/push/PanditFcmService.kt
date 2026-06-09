package com.pandit.android.push

import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import androidx.core.app.NotificationCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import com.pandit.android.MainActivity
import com.pandit.android.PanditApplication
import com.pandit.android.R
import com.pandit.android.data.repository.AuthRepository
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import javax.inject.Inject

@AndroidEntryPoint
class PanditFcmService : FirebaseMessagingService() {

    @Inject lateinit var authRepository: AuthRepository

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onNewToken(token: String) {
        // Register the new FCM token with our backend
        serviceScope.launch { authRepository.registerFcmToken(token) }
    }

    override fun onMessageReceived(message: RemoteMessage) {
        val channelId = when (message.data["type"]) {
            "daily" -> PanditApplication.CHANNEL_DAILY
            else -> PanditApplication.CHANNEL_REMINDERS
        }

        val title = message.notification?.title ?: message.data["title"] ?: getString(R.string.app_name)
        val body = message.notification?.body ?: message.data["body"] ?: return

        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP
            message.data["deep_link"]?.let { putExtra("deep_link", it) }
        }
        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        val notification = NotificationCompat.Builder(this, channelId)
            .setSmallIcon(android.R.drawable.ic_dialog_info) // TODO(design): replace with app icon
            .setContentTitle(title)
            .setContentText(body)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .build()

        val notifId = System.currentTimeMillis().toInt()
        getSystemService(NotificationManager::class.java).notify(notifId, notification)
    }

    override fun onDestroy() {
        super.onDestroy()
        serviceScope.coroutineContext[SupervisorJob]?.cancel()
    }
}
