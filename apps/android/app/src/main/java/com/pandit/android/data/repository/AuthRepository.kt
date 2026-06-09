package com.pandit.android.data.repository

import com.pandit.android.data.api.ApiService
import com.pandit.android.data.api.EmailAuthDto
import com.pandit.android.data.api.FcmTokenDto
import com.pandit.android.data.api.GoogleAuthDto
import com.pandit.android.data.api.ProfileDto
import com.pandit.android.util.TokenStore
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject
import javax.inject.Singleton

sealed class AuthState {
    object Unknown : AuthState()
    object Guest : AuthState()
    data class Authenticated(val profile: ProfileDto) : AuthState()
    object SignedOut : AuthState()
}

@Singleton
class AuthRepository @Inject constructor(
    private val api: ApiService,
    private val tokenStore: TokenStore,
) {
    private val _authState = MutableStateFlow<AuthState>(AuthState.Unknown)
    val authState: StateFlow<AuthState> = _authState.asStateFlow()

    suspend fun init() {
        if (tokenStore.accessToken != null) {
            loadProfile()
        } else {
            _authState.value = AuthState.SignedOut
        }
    }

    suspend fun signInWithGoogle(idToken: String): Result<Unit> = runCatching {
        val tokens = api.signInWithGoogle(GoogleAuthDto(idToken)).data
        tokenStore.accessToken = tokens.accessToken
        tokenStore.refreshToken = tokens.refreshToken
        loadProfile()
    }.fold({ Result.Success(it) }, { Result.Error(it) })

    suspend fun signInWithEmail(email: String, password: String): Result<Unit> = runCatching {
        val tokens = api.signInWithEmail(EmailAuthDto(email, password)).data
        tokenStore.accessToken = tokens.accessToken
        tokenStore.refreshToken = tokens.refreshToken
        loadProfile()
    }.fold({ Result.Success(it) }, { Result.Error(it) })

    suspend fun signInAsGuest(): Result<Unit> = runCatching {
        val tokens = api.signInAsGuest().data
        tokenStore.accessToken = tokens.accessToken
        tokenStore.refreshToken = tokens.refreshToken
        _authState.value = AuthState.Guest
    }.fold({ Result.Success(it) }, { Result.Error(it) })

    suspend fun signOut() {
        runCatching { api.signOut() }
        tokenStore.clear()
        _authState.value = AuthState.SignedOut
    }

    suspend fun registerFcmToken(fcmToken: String) {
        runCatching { api.registerFcmToken(FcmTokenDto(fcmToken)) }
    }

    private suspend fun loadProfile() {
        runCatching { api.getProfile().data }
            .onSuccess { _authState.value = AuthState.Authenticated(it) }
            .onFailure { _authState.value = AuthState.SignedOut }
    }
}
