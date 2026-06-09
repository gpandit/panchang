package com.pandit.android.ui.profile

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.pandit.android.data.api.LocationInputDto
import com.pandit.android.data.api.ProfileDto
import com.pandit.android.data.repository.AuthRepository
import com.pandit.android.data.repository.AuthState
import com.pandit.android.data.repository.Result
import com.pandit.android.util.PrefsStore
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ProfileUiState(
    val profile: ProfileDto? = null,
    val isLoading: Boolean = false,
    val isGuest: Boolean = false,
    val timeFormat: String = "12h",
    val ayanamsa: String = "lahiri",
    val monthScheme: String = "amanta",
)

@HiltViewModel
class ProfileViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    private val prefsStore: PrefsStore,
) : ViewModel() {

    private val _uiState = MutableStateFlow(ProfileUiState())
    val uiState: StateFlow<ProfileUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            authRepository.authState.collect { state ->
                when (state) {
                    is AuthState.Authenticated -> _uiState.update {
                        it.copy(profile = state.profile, isGuest = false)
                    }
                    is AuthState.Guest -> _uiState.update { it.copy(isGuest = true) }
                    else -> Unit
                }
            }
        }
        viewModelScope.launch {
            combine(prefsStore.timeFormat, prefsStore.ayanamsa, prefsStore.monthScheme)
            { tf, ay, ms -> Triple(tf, ay, ms) }.collect { (tf, ay, ms) ->
                _uiState.update { it.copy(timeFormat = tf, ayanamsa = ay, monthScheme = ms) }
            }
        }
    }

    fun setTimeFormat(value: String) = viewModelScope.launch { prefsStore.setTimeFormat(value) }
    fun setAyanamsa(value: String) = viewModelScope.launch { prefsStore.setAyanamsa(value) }
    fun setMonthScheme(value: String) = viewModelScope.launch { prefsStore.setMonthScheme(value) }

    fun signOut() = viewModelScope.launch { authRepository.signOut() }
}
