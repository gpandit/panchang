package com.pandit.android.data.db.dao

import androidx.room.*
import com.pandit.android.data.db.entity.FestivalEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface FestivalDao {

    @Query("SELECT * FROM festivals_cache ORDER BY date ASC")
    fun observeAll(): Flow<List<FestivalEntity>>

    @Query("SELECT * FROM festivals_cache WHERE id = :id")
    fun observeById(id: String): Flow<FestivalEntity?>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertAll(festivals: List<FestivalEntity>)

    @Query("UPDATE festivals_cache SET detailJson = :detail WHERE id = :id")
    suspend fun updateDetail(id: String, detail: String)

    @Query("DELETE FROM festivals_cache WHERE cachedAtMs < :olderThanMs")
    suspend fun evictOld(olderThanMs: Long)
}
