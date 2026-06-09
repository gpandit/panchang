package com.pandit.android.ui.calendar

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.pandit.android.data.api.DailyPanchangDto
import com.pandit.android.data.api.MonthCalendarDto
import com.pandit.android.data.api.NoteDto
import com.pandit.android.data.api.ReminderInputDto
import com.pandit.android.data.repository.NoteRepository
import com.pandit.android.data.repository.PanchangRepository
import com.pandit.android.data.repository.Result
import com.pandit.android.util.LocationHelper
import com.pandit.android.util.PrefsStore
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.YearMonth
import java.time.format.DateTimeFormatter
import javax.inject.Inject

data class CalendarUiState(
    val yearMonth: YearMonth = YearMonth.now(),
    val selectedDate: LocalDate = LocalDate.now(),
    val monthData: MonthCalendarDto? = null,
    val selectedDayData: DailyPanchangDto? = null,
    val notes: List<NoteDto> = emptyList(),
    val isLoadingMonth: Boolean = true,
    val isLoadingDay: Boolean = false,
    val isOffline: Boolean = false,
    val timeFormat: String = "12h",
    val showAddNote: Boolean = false,
    val showAddReminder: Boolean = false,
)

@HiltViewModel
class CalendarViewModel @Inject constructor(
    private val panchangRepository: PanchangRepository,
    private val noteRepository: NoteRepository,
    private val locationHelper: LocationHelper,
    private val prefsStore: PrefsStore,
) : ViewModel() {

    private val _uiState = MutableStateFlow(CalendarUiState())
    val uiState: StateFlow<CalendarUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            prefsStore.timeFormat.collect { fmt -> _uiState.update { it.copy(timeFormat = fmt) } }
        }
        loadMonth(YearMonth.now())
        observeNotes(LocalDate.now())
    }

    fun selectDate(date: LocalDate) {
        _uiState.update { it.copy(selectedDate = date) }
        loadDay(date)
        observeNotes(date)
    }

    fun previousMonth() {
        val ym = _uiState.value.yearMonth.minusMonths(1)
        _uiState.update { it.copy(yearMonth = ym) }
        loadMonth(ym)
    }

    fun nextMonth() {
        val ym = _uiState.value.yearMonth.plusMonths(1)
        _uiState.update { it.copy(yearMonth = ym) }
        loadMonth(ym)
    }

    fun addNote(body: String) = viewModelScope.launch {
        val date = _uiState.value.selectedDate.format(DateTimeFormatter.ISO_LOCAL_DATE)
        noteRepository.createNote(date, body, emptyList())
        _uiState.update { it.copy(showAddNote = false) }
    }

    fun addReminder(title: String, triggerType: String, triggerValue: String, advanceMinutes: Int) =
        viewModelScope.launch {
            noteRepository.createReminder(
                ReminderInputDto(title, triggerType, triggerValue, advanceMinutes)
            )
            _uiState.update { it.copy(showAddReminder = false) }
        }

    fun toggleBookmark() = viewModelScope.launch {
        val date = _uiState.value.selectedDate.format(DateTimeFormatter.ISO_LOCAL_DATE)
        noteRepository.toggleBookmark(date)
    }

    fun showAddNote(show: Boolean) = _uiState.update { it.copy(showAddNote = show) }
    fun showAddReminder(show: Boolean) = _uiState.update { it.copy(showAddReminder = show) }

    private fun loadMonth(ym: YearMonth) = viewModelScope.launch {
        _uiState.update { it.copy(isLoadingMonth = true) }
        val loc = runCatching { locationHelper.currentLocation() }
            .getOrElse { locationHelper.defaultLocation() }
        val ayanamsa = prefsStore.ayanamsa.first()
        val monthScheme = prefsStore.monthScheme.first()
        val key = PanchangRepository.monthKey(ym.year, ym.monthValue, loc.lat, loc.lon)

        // Show cached first
        panchangRepository.observeMonth(key).filterNotNull().take(1).collect { cached ->
            _uiState.update { it.copy(monthData = cached, isLoadingMonth = false) }
        }

        when (val r = panchangRepository.fetchMonth(ym.year, ym.monthValue, loc.lat, loc.lon, loc.tz, ayanamsa, monthScheme)) {
            is Result.Success -> _uiState.update { it.copy(monthData = r.data, isLoadingMonth = false, isOffline = false) }
            is Result.Error -> _uiState.update { it.copy(isLoadingMonth = false, isOffline = true) }
        }
    }

    private fun loadDay(date: LocalDate) = viewModelScope.launch {
        _uiState.update { it.copy(isLoadingDay = true) }
        val loc = runCatching { locationHelper.currentLocation() }
            .getOrElse { locationHelper.defaultLocation() }
        val dateStr = date.format(DateTimeFormatter.ISO_LOCAL_DATE)
        val ayanamsa = prefsStore.ayanamsa.first()
        val monthScheme = prefsStore.monthScheme.first()

        when (val r = panchangRepository.fetchDay(dateStr, loc.lat, loc.lon, loc.tz, ayanamsa, monthScheme)) {
            is Result.Success -> _uiState.update { it.copy(selectedDayData = r.data, isLoadingDay = false) }
            is Result.Error -> _uiState.update { it.copy(isLoadingDay = false) }
        }
    }

    private fun observeNotes(date: LocalDate) {
        val dateStr = date.format(DateTimeFormatter.ISO_LOCAL_DATE)
        viewModelScope.launch {
            noteRepository.observeNotesForDate(dateStr).collect { notes ->
                _uiState.update { it.copy(notes = notes) }
            }
        }
    }
}
