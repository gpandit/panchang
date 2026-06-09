package com.pandit.android.data.db.dao

import androidx.room.*
import com.pandit.android.data.db.entity.DailyPanchangEntity
import com.pandit.android.data.db.entity.MonthCalendarEntity
import com.pandit.android.data.db.entity.TodayEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface PanchangDao {

    // Today

    @Query("SELECT * FROM today_cache WHERE cacheKey = :key")
    fun observeToday(key: String): Flow<TodayEntity?>

    @Query("SELECT * FROM today_cache WHERE cacheKey = :key")
    suspend fun getToday(key: String): TodayEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertToday(entity: TodayEntity)

    // Day

    @Query("SELECT * FROM daily_panchang_cache WHERE cacheKey = :key")
    fun observeDay(key: String): Flow<DailyPanchangEntity?>

    @Query("SELECT * FROM daily_panchang_cache WHERE cacheKey = :key")
    suspend fun getDay(key: String): DailyPanchangEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertDay(entity: DailyPanchangEntity)

    // Month

    @Query("SELECT * FROM month_calendar_cache WHERE cacheKey = :key")
    fun observeMonth(key: String): Flow<MonthCalendarEntity?>

    @Query("SELECT * FROM month_calendar_cache WHERE cacheKey = :key")
    suspend fun getMonth(key: String): MonthCalendarEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertMonth(entity: MonthCalendarEntity)

    // Eviction: keep only the last 60 days to bound storage

    @Query(
        """
        DELETE FROM daily_panchang_cache
        WHERE cachedAtMs < :olderThanMs
        """
    )
    suspend fun evictOldDays(olderThanMs: Long)

    @Query(
        """
        DELETE FROM today_cache
        WHERE cachedAtMs < :olderThanMs
        """
    )
    suspend fun evictOldToday(olderThanMs: Long)

    @Query(
        """
        DELETE FROM month_calendar_cache
        WHERE cachedAtMs < :olderThanMs
        """
    )
    suspend fun evictOldMonths(olderThanMs: Long)
}
