package com.pandit.android

import app.cash.turbine.test
import com.pandit.android.data.api.*
import com.pandit.android.data.db.dao.PanchangDao
import com.pandit.android.data.db.entity.TodayEntity
import com.pandit.android.data.repository.PanchangRepository
import com.pandit.android.data.repository.Result
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import io.mockk.*
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.runTest
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

class PanchangRepositoryTest {

    private val api = mockk<ApiService>()
    private val dao = mockk<PanchangDao>(relaxed = true)
    private val moshi = Moshi.Builder().addLast(KotlinJsonAdapterFactory()).build()

    private lateinit var repo: PanchangRepository

    @Before
    fun setUp() {
        repo = PanchangRepository(api, dao, moshi)
    }

    @Test
    fun `fetchToday returns Success and persists to dao`() = runTest {
        val dto = fakeTodayDto()
        coEvery { api.getTodayView(any(), any(), any(), any(), any()) } returns ApiResponse(dto)

        val result = repo.fetchToday(28.6, 77.2, "Asia/Kolkata", "lahiri", "amanta")

        assertTrue(result is Result.Success)
        coVerify { dao.upsertToday(any()) }
    }

    @Test
    fun `fetchToday returns Error when network throws`() = runTest {
        coEvery { api.getTodayView(any(), any(), any(), any(), any()) } throws Exception("timeout")

        val result = repo.fetchToday(28.6, 77.2, "Asia/Kolkata", "lahiri", "amanta")

        assertTrue(result is Result.Error)
        coVerify(exactly = 0) { dao.upsertToday(any()) }
    }

    @Test
    fun `observeToday emits null when cache is empty`() = runTest {
        every { dao.observeToday(any()) } returns flowOf(null)

        repo.observeToday("key").test {
            assertNull(awaitItem())
            cancelAndIgnoreRemainingEvents()
        }
    }

    @Test
    fun `observeToday deserialises cached payload`() = runTest {
        val dto = fakeTodayDto()
        val adapter = moshi.adapter(DailyPanchangViewDto::class.java)
        val entity = TodayEntity(
            cacheKey = "k", date = dto.date, lat = 28.6, lon = 77.2,
            jsonPayload = adapter.toJson(dto), cachedAtMs = 0,
        )
        every { dao.observeToday("k") } returns flowOf(entity)

        repo.observeToday("k").test {
            val emitted = awaitItem()
            assertNotNull(emitted)
            assertEquals(dto.date, emitted?.date)
            cancelAndIgnoreRemainingEvents()
        }
    }

    @Test
    fun `cacheKey helpers produce consistent keys`() {
        val key1 = PanchangRepository.todayKey("2025-01-01", 28.6, 77.2)
        val key2 = PanchangRepository.todayKey("2025-01-01", 28.6, 77.2)
        assertEquals(key1, key2)
    }

    private fun fakeTodayDto() = DailyPanchangViewDto(
        date = "2025-01-01",
        location = "New Delhi",
        tithi = fakePanchangElement("tithi", "Pratipada"),
        nakshatra = fakePanchangElement("nakshatra", "Ashwini"),
        yoga = fakePanchangElement("yoga", "Vishkumbha"),
        karana = fakePanchangElement("karana", "Kimstughna"),
        vara = fakePanchangElement("vara", "Ravivara"),
        sunrise = fakeTime("06:30"),
        sunset = fakeTime("18:00"),
        moonrise = null,
        moonset = null,
        muhurats = emptyList(),
        festivals = emptyList(),
        advisory = AdvisoryDto(goodFor = listOf("Travel"), avoid = listOf("Surgery")),
        highlights = emptyList(),
        dharmaCard = null,
    )

    private fun fakePanchangElement(key: String, value: String) = PanchangElementDto(
        key = key, label = key.replaceFirstChar { it.uppercase() },
        value = value, startTime = null, endTime = null, explanationKey = key,
    )

    private fun fakeTime(t: String) = TimeValueDto(
        iso = "2025-01-01T${t}:00+05:30",
        hour24 = t,
        hour12 = t,
        hour24Plus = t,
    )
}
