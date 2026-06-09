package com.pandit.android

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import com.pandit.android.data.db.PanditDatabase
import com.pandit.android.data.db.dao.PanchangDao
import com.pandit.android.data.db.entity.TodayEntity
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

/**
 * Verifies the offline cache layer using an in-memory Room database.
 * This is a JVM unit test via Robolectric (no emulator needed).
 */
@RunWith(RobolectricTestRunner::class)
class OfflineCacheTest {

    private lateinit var db: PanditDatabase
    private lateinit var dao: PanchangDao

    @Before
    fun setUp() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        db = Room.inMemoryDatabaseBuilder(context, PanditDatabase::class.java)
            .allowMainThreadQueries()
            .build()
        dao = db.panchangDao()
    }

    @After
    fun tearDown() = db.close()

    @Test
    fun `upsert and observe today entity round-trips`() = runTest {
        val entity = TodayEntity(
            cacheKey = "2025-01-01_28.6_77.2",
            date = "2025-01-01",
            lat = 28.6, lon = 77.2,
            jsonPayload = """{"date":"2025-01-01"}""",
            cachedAtMs = 1000L,
        )

        dao.upsertToday(entity)

        val fetched = dao.observeToday("2025-01-01_28.6_77.2").first()
        assertNotNull(fetched)
        assertEquals("2025-01-01", fetched?.date)
    }

    @Test
    fun `evictOldToday removes stale entries`() = runTest {
        val entity = TodayEntity(
            cacheKey = "old",
            date = "2024-01-01",
            lat = 28.6, lon = 77.2,
            jsonPayload = "{}",
            cachedAtMs = 1000L,
        )
        dao.upsertToday(entity)

        dao.evictOldToday(2000L)

        assertNull(dao.getToday("old"))
    }

    @Test
    fun `upsert replaces existing entry`() = runTest {
        val key = "k"
        dao.upsertToday(TodayEntity(key, "2025-01-01", 0.0, 0.0, """{"v":1}""", 0L))
        dao.upsertToday(TodayEntity(key, "2025-01-01", 0.0, 0.0, """{"v":2}""", 1L))

        val fetched = dao.getToday(key)
        assertEquals("""{"v":2}""", fetched?.jsonPayload)
    }
}
