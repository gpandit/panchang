package com.pandit.android.util

import android.annotation.SuppressLint
import android.content.Context
import android.location.Location
import com.google.android.gms.location.CurrentLocationRequest
import com.google.android.gms.location.Granularity
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import com.google.android.gms.tasks.CancellationTokenSource
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.suspendCancellableCoroutine
import java.util.TimeZone
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

data class DeviceLocation(val lat: Double, val lon: Double, val tz: String)

@Singleton
class LocationHelper @Inject constructor(@ApplicationContext private val context: Context) {

    private val fusedClient = LocationServices.getFusedLocationProviderClient(context)

    @SuppressLint("MissingPermission")
    suspend fun currentLocation(): DeviceLocation {
        val cts = CancellationTokenSource()
        return suspendCancellableCoroutine { cont ->
            cont.invokeOnCancellation { cts.cancel() }
            val req = CurrentLocationRequest.Builder()
                .setPriority(Priority.PRIORITY_BALANCED_POWER_ACCURACY)
                .setGranularity(Granularity.GRANULARITY_PERMISSION_LEVEL)
                .build()
            fusedClient.getCurrentLocation(req, cts.token)
                .addOnSuccessListener { loc: Location? ->
                    if (loc != null) {
                        cont.resume(
                            DeviceLocation(
                                lat = loc.latitude,
                                lon = loc.longitude,
                                tz = TimeZone.getDefault().id,
                            )
                        )
                    } else {
                        cont.resumeWithException(IllegalStateException("Location unavailable"))
                    }
                }
                .addOnFailureListener { cont.resumeWithException(it) }
        }
    }

    fun defaultLocation(): DeviceLocation =
        DeviceLocation(lat = 28.6139, lon = 77.2090, tz = "Asia/Kolkata") // New Delhi fallback
}
