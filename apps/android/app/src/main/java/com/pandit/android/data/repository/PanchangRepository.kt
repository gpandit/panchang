package com.pandit.android.data.repository

import com.pandit.android.data.api.ApiService
import com.pandit.android.data.api.DailyPanchangDto
import com.pandit.android.data.api.DailyPanchangViewDto
import com.pandit.android.data.api.MonthCalendarDto
import com.pandit.android.data.db.dao.PanchangDao
import com.pandit.android.data.db.entity.DailyPanchangEntity
import com.pandit.android.data.db.entity.MonthCalendarEntity
import com.pandit.android.data.db.entity.TodayEntity
import com.squareup.moshi.Moshi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

sealed class Result<out T> {
    data class Success<T>(val data: T) : Result<T>()
    data class Error(val cause: Throwable) : Result<Nothing>()
}

@Singleton
class PanchangRepository @Inject constructor(
    private val api: ApiService,
    private val dao: PanchangDao,
    private val moshi: Moshi,
) {
    private val todayAdapter by lazy { moshi.adapter(DailyPanchangViewDto::class.java) }
    private val dayAdapter by lazy { moshi.adapter(DailyPanchangDto::class.java) }
    private val monthAdapter by lazy { moshi.adapter(MonthCalendarDto::class.java) }

    // ── Today ─────────────────────────────────────────────────────────────────

    fun observeToday(key: String): Flow<DailyPanchangViewDto?> =
        dao.observeToday(key).map { it?.let { e -> todayAdapter.fromJson(e.jsonPayload) } }

    suspend fun fetchToday(
        lat: Double, lon: Double, tz: String, ayanamsa: String, monthScheme: String
    ): Result<DailyPanchangViewDto> = runCatching {
        val dto = api.getTodayView(lat, lon, tz, ayanamsa, monthScheme).data
        val date = dto.date
        dao.upsertToday(
            TodayEntity(
                cacheKey = todayKey(date, lat, lon),
                date = date,
                lat = lat,
                lon = lon,
                jsonPayload = todayAdapter.toJson(dto),
                cachedAtMs = System.currentTimeMillis(),
            )
        )
        dto
    }.fold({ Result.Success(it) }, { Result.Error(it) })

    // ── Day ───────────────────────────────────────────────────────────────────

    fun observeDay(key: String): Flow<DailyPanchangDto?> =
        dao.observeDay(key).map { it?.let { e -> dayAdapter.fromJson(e.jsonPayload) } }

    suspend fun fetchDay(
        date: String, lat: Double, lon: Double, tz: String,
        ayanamsa: String, monthScheme: String,
    ): Result<DailyPanchangDto> = runCatching {
        val dto = api.getDayPanchang(date, lat, lon, tz, ayanamsa, monthScheme).data
        dao.upsertDay(
            DailyPanchangEntity(
                cacheKey = dayKey(date, lat, lon),
                date = date, lat = lat, lon = lon, tz = tz,
                jsonPayload = dayAdapter.toJson(dto),
                cachedAtMs = System.currentTimeMillis(),
            )
        )
        dto
    }.fold({ Result.Success(it) }, { Result.Error(it) })

    // ── Month ─────────────────────────────────────────────────────────────────

    fun observeMonth(key: String): Flow<MonthCalendarDto?> =
        dao.observeMonth(key).map { it?.let { e -> monthAdapter.fromJson(e.jsonPayload) } }

    suspend fun fetchMonth(
        year: Int, month: Int, lat: Double, lon: Double, tz: String,
        ayanamsa: String, monthScheme: String,
    ): Result<MonthCalendarDto> = runCatching {
        val dto = api.getMonthCalendar(year, month, lat, lon, tz, ayanamsa, monthScheme).data
        dao.upsertMonth(
            MonthCalendarEntity(
                cacheKey = monthKey(year, month, lat, lon),
                year = year, month = month, lat = lat, lon = lon,
                jsonPayload = monthAdapter.toJson(dto),
                cachedAtMs = System.currentTimeMillis(),
            )
        )
        dto
    }.fold({ Result.Success(it) }, { Result.Error(it) })

    // ── Explanation ───────────────────────────────────────────────────────────

    suspend fun fetchExplanation(key: String): Result<String> = runCatching {
        api.getExplanation(key)["data"]?.get("text")?.toString() ?: ""
    }.fold({ Result.Success(it) }, { Result.Error(it) })

    // ── Cache eviction ────────────────────────────────────────────────────────

    suspend fun evictOldCache(olderThanMs: Long) {
        dao.evictOldDays(olderThanMs)
        dao.evictOldToday(olderThanMs)
        dao.evictOldMonths(olderThanMs)
    }

    companion object {
        fun todayKey(date: String, lat: Double, lon: Double) = "${date}_${lat}_${lon}"
        fun dayKey(date: String, lat: Double, lon: Double) = "${date}_${lat}_${lon}"
        fun monthKey(year: Int, month: Int, lat: Double, lon: Double) = "${year}_${month}_${lat}_${lon}"
    }
}
