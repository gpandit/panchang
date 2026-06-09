package com.pandit.android.ui.auth

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.pandit.android.R

// TODO(design): layout, spacing, typography, and visual treatment deferred to design system.

@Composable
fun AuthScreen(
    onAuthSuccess: () -> Unit,
    viewModel: AuthViewModel = hiltViewModel(),
) {
    val uiState by viewModel.uiState.collectAsState()
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var showEmailForm by remember { mutableStateOf(false) }

    LaunchedEffect(uiState) {
        if (!uiState.isLoading && uiState.error == null) {
            // navigation driven by authState observer in NavHost
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = stringResource(R.string.app_name),
            style = MaterialTheme.typography.titleLarge,
        )

        Spacer(Modifier.height(48.dp))

        if (uiState.isLoading) {
            CircularProgressIndicator()
        } else {
            Button(
                onClick = { /* TODO: launch Google Sign-In intent */ },
                modifier = Modifier
                    .fillMaxWidth()
                    .semantics { contentDescription = "Sign in with Google" },
            ) {
                Text(stringResource(R.string.sign_in_google))
            }

            Spacer(Modifier.height(16.dp))

            OutlinedButton(
                onClick = { showEmailForm = !showEmailForm },
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(stringResource(R.string.sign_in_email))
            }

            if (showEmailForm) {
                Spacer(Modifier.height(16.dp))
                OutlinedTextField(
                    value = email,
                    onValueChange = { email = it },
                    label = { Text(stringResource(R.string.email_label)) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                )
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = password,
                    onValueChange = { password = it },
                    label = { Text(stringResource(R.string.password_label)) },
                    visualTransformation = PasswordVisualTransformation(),
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                )
                Spacer(Modifier.height(8.dp))
                Button(
                    onClick = { viewModel.signInWithEmail(email, password) },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = email.isNotBlank() && password.isNotBlank(),
                ) {
                    Text(stringResource(R.string.sign_in_email))
                }
            }

            Spacer(Modifier.height(16.dp))

            TextButton(
                onClick = { viewModel.signInAsGuest() },
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(stringResource(R.string.sign_in_guest))
            }
        }

        uiState.error?.let { error ->
            Spacer(Modifier.height(16.dp))
            Text(
                text = error,
                color = MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}
