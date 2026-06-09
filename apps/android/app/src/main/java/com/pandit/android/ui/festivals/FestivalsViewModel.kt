package com.pandit.android.ui.festivals

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.pandit.android.data.api.FestivalDetailDto
import com.pandit.android.data.api.FestivalDto
import com.pandit.android.data.repository.FestivalRepository
import com.pandit.android.data.repository.Result
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class FestivalsUiState(
    val festivals: List<FestivalDto> = emptyList(),
    val isLoading: Boolean = true,
    val isOffline: Boolean = false,
    val error: String? = null,
)

data class FestivalDetailUiState(
    val detail: FestivalDetailDto? = null,
    val isLoading: Boolean = true,
    val error: String? = null,
)

@HiltViewModel
class FestivalsViewModel @Inject constructor(
    private val festivalRepository: FestivalRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(FestivalsUiState())
    val uiState: StateFlow<FestivalsUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            festivalRepository.observeAll().collect { list ->
                _uiState.update { it.copy(festivals = list, isLoading = false) }
            }
        }
        refresh()
    }

    fun refresh() = viewModelScope.launch {
        when (val r = festivalRepository.fetchFestivals()) {
            is Result.Success -> _uiState.update { it.copy(isOffline = false, error = null) }
            is Result.Error -> _uiState.update { it.copy(isOffline = true) }
        }
    }
}

@HiltViewModel
class FestivalDetailViewModel @Inject constructor(
    private val festivalRepository: FestivalRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(FestivalDetailUiState())
    val uiState: StateFlow<FestivalDetailUiState> = _uiState.asStateFlow()

    fun load(id: String) = viewModelScope.launch {
        festivalRepository.observeDetail(id).filterNotNull().take(1).collect { cached ->
            _uiState.update { it.copy(detail = cached, isLoading = false) }
        }
        when (val r = festivalRepository.fetchDetail(id)) {
            is Result.Success -> _uiState.update { it.copy(detail = r.data, isLoading = false, error = null) }
            is Result.Error -> _uiState.update { it.copy(isLoading = false, error = r.cause.message) }
        }
    }
}
