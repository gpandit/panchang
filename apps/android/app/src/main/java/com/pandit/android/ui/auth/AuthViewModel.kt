package com.pandit.android.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.pandit.android.data.repository.AuthRepository
import com.pandit.android.data.repository.AuthState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AuthUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val authRepository: AuthRepository,
) : ViewModel() {

    val authState: StateFlow<AuthState> = authRepository.authState

    private val _uiState = kotlinx.coroutines.flow.MutableStateFlow(AuthUiState())
    val uiState: StateFlow<AuthUiState> = _uiState

    init {
        viewModelScope.launch { authRepository.init() }
    }

    fun signInWithGoogle(idToken: String) = viewModelScope.launch {
        _uiState.value = AuthUiState(isLoading = true)
        authRepository.signInWithGoogle(idToken)
            .let { result ->
                _uiState.value = when (result) {
                    is com.pandit.android.data.repository.Result.Success -> AuthUiState()
                    is com.pandit.android.data.repository.Result.Error ->
                        AuthUiState(error = result.cause.message)
                }
            }
    }

    fun signInWithEmail(email: String, password: String) = viewModelScope.launch {
        _uiState.value = AuthUiState(isLoading = true)
        authRepository.signInWithEmail(email, password)
            .let { result ->
                _uiState.value = when (result) {
                    is com.pandit.android.data.repository.Result.Success -> AuthUiState()
                    is com.pandit.android.data.repository.Result.Error ->
                        AuthUiState(error = result.cause.message)
                }
            }
    }

    fun signInAsGuest() = viewModelScope.launch {
        _uiState.value = AuthUiState(isLoading = true)
        authRepository.signInAsGuest()
            .let { result ->
                _uiState.value = when (result) {
                    is com.pandit.android.data.repository.Result.Success -> AuthUiState()
                    is com.pandit.android.data.repository.Result.Error ->
                        AuthUiState(error = result.cause.message)
                }
            }
    }

    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }
}
