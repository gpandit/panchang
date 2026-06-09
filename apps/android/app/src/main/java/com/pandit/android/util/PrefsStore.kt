package com.pandit.android.util

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.dataStore by preferencesDataStore("pandit_prefs")

/** Time format preference: "12h", "24h", or "24plus". */
@Singleton
class PrefsStore @Inject constructor(@ApplicationContext private val context: Context) {

    private val KEY_TIME_FORMAT = stringPreferencesKey("time_format")
    private val KEY_AYANAMSA = stringPreferencesKey("ayanamsa")
    private val KEY_MONTH_SCHEME = stringPreferencesKey("month_scheme")

    val timeFormat: Flow<String> = context.dataStore.data.map { it[KEY_TIME_FORMAT] ?: "12h" }
    val ayanamsa: Flow<String> = context.dataStore.data.map { it[KEY_AYANAMSA] ?: "lahiri" }
    val monthScheme: Flow<String> = context.dataStore.data.map { it[KEY_MONTH_SCHEME] ?: "amanta" }

    suspend fun setTimeFormat(value: String) {
        context.dataStore.edit { it[KEY_TIME_FORMAT] = value }
    }

    suspend fun setAyanamsa(value: String) {
        context.dataStore.edit { it[KEY_AYANAMSA] = value }
    }

    suspend fun setMonthScheme(value: String) {
        context.dataStore.edit { it[KEY_MONTH_SCHEME] = value }
    }
}
