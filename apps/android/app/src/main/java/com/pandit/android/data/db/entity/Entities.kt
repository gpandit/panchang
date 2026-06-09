package com.pandit.android.data.db.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "daily_panchang_cache")
data class DailyPanchangEntity(
    @PrimaryKey val cacheKey: String, // "YYYY-MM-DD_lat_lon"
    val date: String,
    val lat: Double,
    val lon: Double,
    val tz: String,
    val jsonPayload: String,          // serialised DailyPanchangDto
    val cachedAtMs: Long,
)

@Entity(tableName = "today_cache")
data class TodayEntity(
    @PrimaryKey val cacheKey: String, // "YYYY-MM-DD_lat_lon"
    val date: String,
    val lat: Double,
    val lon: Double,
    val jsonPayload: String,          // serialised DailyPanchangViewDto
    val cachedAtMs: Long,
)

@Entity(tableName = "month_calendar_cache")
data class MonthCalendarEntity(
    @PrimaryKey val cacheKey: String, // "YYYY-MM_lat_lon"
    val year: Int,
    val month: Int,
    val lat: Double,
    val lon: Double,
    val jsonPayload: String,          // serialised MonthCalendarDto
    val cachedAtMs: Long,
)

@Entity(tableName = "festivals_cache")
data class FestivalEntity(
    @PrimaryKey val id: String,
    val name: String,
    val date: String,
    val description: String?,
    val tagsJson: String,
    val region: String?,
    val locale: String?,
    val detailJson: String?,          // nullable until detail is fetched
    val cachedAtMs: Long,
)

@Entity(tableName = "notes")
data class NoteEntity(
    @PrimaryKey val id: String,
    val date: String,
    val body: String,
    val tagsJson: String,
    val createdAt: String,
    val updatedAt: String,
    val isDirty: Boolean = false,     // pending sync
    val isDeleted: Boolean = false,
)

@Entity(tableName = "reminders")
data class ReminderEntity(
    @PrimaryKey val id: String,
    val title: String,
    val triggerType: String,
    val triggerValue: String,
    val advanceMinutes: Int,
    val nextFireAt: String?,
    val isActive: Boolean,
    val isDirty: Boolean = false,
)

@Entity(tableName = "bookmarks")
data class BookmarkEntity(
    @PrimaryKey val date: String,
    val createdAtMs: Long,
)
