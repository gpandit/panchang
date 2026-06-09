package com.pandit.android

import app.cash.turbine.test
import com.pandit.android.data.api.*
import com.pandit.android.data.repository.NoteRepository
import com.pandit.android.data.repository.PanchangRepository
import com.pandit.android.data.repository.Result
import com.pandit.android.ui.today.TodayViewModel
import com.pandit.android.util.DeviceLocation
import com.pandit.android.util.LocationHelper
import com.pandit.android.util.PrefsStore
import io.mockk.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.*
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class TodayViewModelTest {

    private val panchangRepo = mockk<PanchangRepository>(relaxed = true)
    private val noteRepo = mockk<NoteRepository>(relaxed = true)
    private val locationHelper = mockk<LocationHelper>()
    private val prefsStore = mockk<PrefsStore>()

    private val testDispatcher = StandardTestDispatcher()

    @Before
    fun setUp() {
        Dispatchers.setMain(testDispatcher)
        every { locationHelper.defaultLocation() } returns DeviceLocation(28.6, 77.2, "Asia/Kolkata")
        coEvery { locationHelper.currentLocation() } returns DeviceLocation(28.6, 77.2, "Asia/Kolkata")
        every { prefsStore.timeFormat } returns flowOf("12h")
        every { prefsStore.ayanamsa } returns flowOf("lahiri")
        every { prefsStore.monthScheme } returns flowOf("amanta")
        coEvery { noteRepo.isBookmarked(any()) } returns false
        every { panchangRepo.observeToday(any()) } returns flowOf(null)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun `initial state is loading`() {
        val vm = TodayViewModel(panchangRepo, noteRepo, locationHelper, prefsStore)
        assertTrue(vm.uiState.value.isLoading)
    }

    @Test
    fun `successful fetch updates panchang in state`() = runTest {
        val dto = fakeTodayDto()
        coEvery { panchangRepo.fetchToday(any(), any(), any(), any(), any()) } returns Result.Success(dto)

        val vm = TodayViewModel(panchangRepo, noteRepo, locationHelper, prefsStore)
        testDispatcher.scheduler.advanceUntilIdle()

        assertNotNull(vm.uiState.value.panchang)
        assertFalse(vm.uiState.value.isOffline)
    }

    @Test
    fun `network failure marks isOffline true`() = runTest {
        coEvery { panchangRepo.fetchToday(any(), any(), any(), any(), any()) } returns
            Result.Error(Exception("no network"))

        val vm = TodayViewModel(panchangRepo, noteRepo, locationHelper, prefsStore)
        testDispatcher.scheduler.advanceUntilIdle()

        assertTrue(vm.uiState.value.isOffline)
    }

    @Test
    fun `setTimeFormat persists to prefs`() = runTest {
        coEvery { panchangRepo.fetchToday(any(), any(), any(), any(), any()) } returns
            Result.Error(Exception())
        val vm = TodayViewModel(panchangRepo, noteRepo, locationHelper, prefsStore)

        vm.setTimeFormat("24h")
        testDispatcher.scheduler.advanceUntilIdle()

        coVerify { prefsStore.setTimeFormat("24h") }
    }

    @Test
    fun `toggleBookmark calls noteRepository`() = runTest {
        val dto = fakeTodayDto()
        coEvery { panchangRepo.fetchToday(any(), any(), any(), any(), any()) } returns Result.Success(dto)
        val vm = TodayViewModel(panchangRepo, noteRepo, locationHelper, prefsStore)
        testDispatcher.scheduler.advanceUntilIdle()

        vm.toggleBookmark()
        testDispatcher.scheduler.advanceUntilIdle()

        coVerify { noteRepo.toggleBookmark(dto.date) }
    }

    private fun fakeTodayDto() = DailyPanchangViewDto(
        date = "2025-01-01", location = "New Delhi",
        tithi = fakeElement("tithi", "Pratipada"),
        nakshatra = fakeElement("nakshatra", "Ashwini"),
        yoga = fakeElement("yoga", "Vishkumbha"),
        karana = fakeElement("karana", "Kimstughna"),
        vara = fakeElement("vara", "Ravivara"),
        sunrise = fakeTime("06:30"), sunset = fakeTime("18:00"),
        moonrise = null, moonset = null,
        muhurats = emptyList(), festivals = emptyList(),
        advisory = AdvisoryDto(emptyList(), emptyList()),
        highlights = emptyList(), dharmaCard = null,
    )

    private fun fakeElement(key: String, value: String) = PanchangElementDto(
        key = key, label = key, value = value,
        startTime = null, endTime = null, explanationKey = key,
    )

    private fun fakeTime(t: String) = TimeValueDto(
        iso = "2025-01-01T${t}:00+05:30", hour24 = t, hour12 = t, hour24Plus = t,
    )
}
