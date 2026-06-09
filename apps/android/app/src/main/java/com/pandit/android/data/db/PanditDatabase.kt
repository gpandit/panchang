package com.pandit.android.data.db

import androidx.room.Database
import androidx.room.RoomDatabase
import com.pandit.android.data.db.dao.*
import com.pandit.android.data.db.entity.*

@Database(
    entities = [
        DailyPanchangEntity::class,
        TodayEntity::class,
        MonthCalendarEntity::class,
        FestivalEntity::class,
        NoteEntity::class,
        ReminderEntity::class,
        BookmarkEntity::class,
    ],
    version = 1,
    exportSchema = true,
)
abstract class PanditDatabase : RoomDatabase() {
    abstract fun panchangDao(): PanchangDao
    abstract fun festivalDao(): FestivalDao
    abstract fun noteDao(): NoteDao
    abstract fun reminderDao(): ReminderDao
    abstract fun bookmarkDao(): BookmarkDao
}
