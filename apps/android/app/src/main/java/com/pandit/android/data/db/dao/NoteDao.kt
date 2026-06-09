package com.pandit.android.data.db.dao

import androidx.room.*
import com.pandit.android.data.db.entity.BookmarkEntity
import com.pandit.android.data.db.entity.NoteEntity
import com.pandit.android.data.db.entity.ReminderEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface NoteDao {

    @Query("SELECT * FROM notes WHERE date = :date AND isDeleted = 0 ORDER BY createdAt DESC")
    fun observeForDate(date: String): Flow<List<NoteEntity>>

    @Query("SELECT * FROM notes WHERE isDeleted = 0 ORDER BY date DESC")
    fun observeAll(): Flow<List<NoteEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(note: NoteEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertAll(notes: List<NoteEntity>)

    @Query("UPDATE notes SET isDeleted = 1, isDirty = 1 WHERE id = :id")
    suspend fun markDeleted(id: String)

    @Query("DELETE FROM notes WHERE isDeleted = 1 AND isDirty = 0")
    suspend fun purgeSynced()
}

@Dao
interface ReminderDao {

    @Query("SELECT * FROM reminders WHERE isActive = 1 ORDER BY nextFireAt ASC")
    fun observeActive(): Flow<List<ReminderEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(reminder: ReminderEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertAll(reminders: List<ReminderEntity>)

    @Query("DELETE FROM reminders WHERE id = :id")
    suspend fun delete(id: String)
}

@Dao
interface BookmarkDao {

    @Query("SELECT * FROM bookmarks ORDER BY date DESC")
    fun observeAll(): Flow<List<BookmarkEntity>>

    @Query("SELECT * FROM bookmarks WHERE date = :date")
    suspend fun get(date: String): BookmarkEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(bookmark: BookmarkEntity)

    @Query("DELETE FROM bookmarks WHERE date = :date")
    suspend fun delete(date: String)
}
