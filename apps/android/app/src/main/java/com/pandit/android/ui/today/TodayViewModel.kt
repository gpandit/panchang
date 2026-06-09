package com.pandit.android.ui.today

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.pandit.android.data.api.DailyPanchangViewDto
import com.pandit.android.data.repository.NoteRepository
import com.pandit.android.data.repository.PanchangRepository
import com.pandit.android.data.repository.Result
import com.pandit.android.util.LocationHelper
import com.pandit.android.util.PrefsStore
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import javax.inject.Inject

data class TodayUiState(
    val isLoading: Boolean = true,
    val isOffline: Boolean = false,
    val error: String? = null,
    val panchang: DailyPanchangViewDto? = null,
    val timeFormat: String = "12h",
    val isBookmarked: Boolean = false,
    val explanation: String? = null,
    val explanationLoading: Boolean = false,
)

@HiltViewModel
class TodayViewModel @Inject constructor(
    private val panchangRepository: PanchangRepository,
    private val noteRepository: NoteRepository,
    private val locationHelper: LocationHelper,
    private val prefsStore: PrefsStore,
) : ViewModel() {

    private val _uiState = MutableStateFlow(TodayUiState())
    val uiState: StateFlow<TodayUiState> = _uiState.asStateFlow()

    private var currentCacheKey: String? = null

    init {
        viewModelScope.launch {
            prefsStore.timeFormat.collect { fmt ->
                _uiState.update { it.copy(timeFormat = fmt) }
            }
        }
        load()
    }

    fun load() = viewModelScope.launch {
        _uiState.update { it.copy(isLoading = true, error = null) }

        val loc = runCatching { locationHelper.currentLocation() }
            .getOrElse { locationHelper.defaultLocation() }

        val today = LocalDate.now().format(DateTimeFormatter.ISO_LOCAL_DATE)
        val key = PanchangRepository.todayKey(today, loc.lat, loc.lon)
        currentCacheKey = key

        val ayanamsa = prefsStore.ayanamsa.first()
        val monthScheme = prefsStore.monthScheme.first()

        // Observe cache — shows immediately if available
        panchangRepository.observeToday(key)
            .filterNotNull()
            .take(1)
            .collect { cached ->
                _uiState.update { it.copy(panchang = cached, isLoading = false) }
                checkBookmark(today)
            }

        // Fetch fresh from network
        when (val result = panchangRepository.fetchToday(loc.lat, loc.lon, loc.tz, ayanamsa, monthScheme)) {
            is Result.Success -> _uiState.update {
                it.copy(panchang = result.data, isLoading = false, isOffline = false, error = null)
            }
            is Result.Error -> _uiState.update { it.copy(isLoading = false, isOffline = true) }
        }

        checkBookmark(today)
    }

    fun setTimeFormat(format: String) = viewModelScope.launch {
        prefsStore.setTimeFormat(format)
    }

    fun toggleBookmark() = viewModelScope.launch {
        val date = _uiState.value.panchang?.date ?: return@launch
        noteRepository.toggleBookmark(date)
        checkBookmark(date)
    }

    fun requestExplanation(key: String) = viewModelScope.launch {
        _uiState.update { it.copy(explanationLoading = true, explanation = null) }
        when (val result = panchangRepository.fetchExplanation(key)) {
            is Result.Success -> _uiState.update {
                it.copy(explanation = result.data, explanationLoading = false)
            }
            is Result.Error -> _uiState.update {
                it.copy(explanationLoading = false, explanation = null)
            }
        }
    }

    fun dismissExplanation() = _uiState.update { it.copy(explanation = null) }

    private suspend fun checkBookmark(date: String) {
        val bookmarked = noteRepository.isBookmarked(date)
        _uiState.update { it.copy(isBookmarked = bookmarked) }
    }
}
