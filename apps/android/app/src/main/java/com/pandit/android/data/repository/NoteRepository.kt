package com.pandit.android.data.repository

import com.pandit.android.data.api.ApiService
import com.pandit.android.data.api.NoteDto
import com.pandit.android.data.api.NoteInputDto
import com.pandit.android.data.api.ReminderDto
import com.pandit.android.data.api.ReminderInputDto
import com.pandit.android.data.db.dao.BookmarkDao
import com.pandit.android.data.db.dao.NoteDao
import com.pandit.android.data.db.dao.ReminderDao
import com.pandit.android.data.db.entity.BookmarkEntity
import com.pandit.android.data.db.entity.NoteEntity
import com.pandit.android.data.db.entity.ReminderEntity
import com.squareup.moshi.Moshi
import com.squareup.moshi.Types
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class NoteRepository @Inject constructor(
    private val api: ApiService,
    private val noteDao: NoteDao,
    private val reminderDao: ReminderDao,
    private val bookmarkDao: BookmarkDao,
    private val moshi: Moshi,
) {
    private val tagsAdapter by lazy {
        moshi.adapter<List<String>>(Types.newParameterizedType(List::class.java, String::class.java))
    }

    // ── Notes ─────────────────────────────────────────────────────────────────

    fun observeNotesForDate(date: String): Flow<List<NoteDto>> =
        noteDao.observeForDate(date).map { it.map { e -> e.toDto() } }

    suspend fun createNote(date: String, body: String, tags: List<String>): Result<NoteDto> =
        runCatching {
            val dto = api.createNote(NoteInputDto(date, body, tags)).data
            noteDao.upsert(dto.toEntity())
            dto
        }.fold({ Result.Success(it) }, { Result.Error(it) })

    suspend fun deleteNote(id: String): Result<Unit> = runCatching {
        noteDao.markDeleted(id)
        api.deleteNote(id)
        noteDao.purgeSynced()
    }.fold({ Result.Success(it) }, { Result.Error(it) })

    suspend fun syncNotes(): Result<Unit> = runCatching {
        val notes = api.getNotes().data
        noteDao.upsertAll(notes.map { it.toEntity() })
    }.fold({ Result.Success(it) }, { Result.Error(it) })

    // ── Reminders ─────────────────────────────────────────────────────────────

    fun observeReminders(): Flow<List<ReminderDto>> =
        reminderDao.observeActive().map { it.map { e -> e.toDto() } }

    suspend fun createReminder(input: ReminderInputDto): Result<ReminderDto> = runCatching {
        val dto = api.createReminder(input).data
        reminderDao.upsert(dto.toEntity())
        dto
    }.fold({ Result.Success(it) }, { Result.Error(it) })

    suspend fun deleteReminder(id: String): Result<Unit> = runCatching {
        reminderDao.delete(id)
        api.deleteReminder(id)
    }.fold({ Result.Success(it) }, { Result.Error(it) })

    // ── Bookmarks ─────────────────────────────────────────────────────────────

    fun observeBookmarks(): Flow<List<BookmarkEntity>> = bookmarkDao.observeAll()

    suspend fun toggleBookmark(date: String) {
        if (bookmarkDao.get(date) != null) {
            bookmarkDao.delete(date)
        } else {
            bookmarkDao.upsert(BookmarkEntity(date, System.currentTimeMillis()))
        }
    }

    suspend fun isBookmarked(date: String): Boolean = bookmarkDao.get(date) != null

    // ── Mappers ───────────────────────────────────────────────────────────────

    private fun NoteDto.toEntity() = NoteEntity(
        id = id, date = date, body = body,
        tagsJson = tagsAdapter.toJson(tags),
        createdAt = createdAt, updatedAt = updatedAt,
    )

    private fun NoteEntity.toDto() = NoteDto(
        id = id, date = date, body = body,
        tags = tagsAdapter.fromJson(tagsJson) ?: emptyList(),
        createdAt = createdAt, updatedAt = updatedAt,
    )

    private fun ReminderDto.toEntity() = ReminderEntity(
        id = id, title = title, triggerType = triggerType,
        triggerValue = triggerValue, advanceMinutes = advanceMinutes,
        nextFireAt = nextFireAt, isActive = isActive,
    )

    private fun ReminderEntity.toDto() = ReminderDto(
        id = id, title = title, triggerType = triggerType,
        triggerValue = triggerValue, advanceMinutes = advanceMinutes,
        nextFireAt = nextFireAt, isActive = isActive,
    )
}
