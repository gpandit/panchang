package com.pandit.android.ui.profile

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.pandit.android.R

// TODO(design): visual styling deferred to Aqualeo design system.

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileScreen(viewModel: ProfileViewModel = hiltViewModel()) {
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = { TopAppBar(title = { Text(stringResource(R.string.nav_profile)) }) }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .padding(paddingValues)
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            // Account section
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Account", style = MaterialTheme.typography.titleSmall)
                    if (uiState.isGuest) {
                        Text("Guest session", style = MaterialTheme.typography.bodyMedium)
                    } else {
                        uiState.profile?.let { p ->
                            p.displayName?.let { Text(it, style = MaterialTheme.typography.bodyMedium) }
                            p.email?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
                        }
                    }
                    Button(
                        onClick = viewModel::signOut,
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.error
                        ),
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        Text(stringResource(R.string.sign_out))
                    }
                }
            }

            // Preferences
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text("Preferences", style = MaterialTheme.typography.titleSmall)

                    // Time format
                    PreferenceRow(
                        label = "Time format",
                        options = listOf("12h" to "12h", "24h" to "24h", "24plus" to "24+"),
                        selected = uiState.timeFormat,
                        onSelect = viewModel::setTimeFormat,
                    )

                    // Ayanamsa (lahiri only for MVP)
                    PreferenceRow(
                        label = "Ayanamsa",
                        options = listOf("lahiri" to "Lahiri (Chitrapaksha)"),
                        selected = uiState.ayanamsa,
                        onSelect = viewModel::setAyanamsa,
                    )

                    // Month scheme
                    PreferenceRow(
                        label = "Month scheme",
                        options = listOf("amanta" to "Amanta", "purnimanta" to "Purnimanta"),
                        selected = uiState.monthScheme,
                        onSelect = viewModel::setMonthScheme,
                    )
                }
            }

            // Locations — list from profile
            uiState.profile?.locations?.let { locations ->
                if (locations.isNotEmpty()) {
                    Card(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text("Saved locations", style = MaterialTheme.typography.titleSmall)
                            locations.forEach { loc ->
                                Row(Modifier.fillMaxWidth()) {
                                    Column(Modifier.weight(1f)) {
                                        Text(loc.name, style = MaterialTheme.typography.bodyMedium)
                                        Text(loc.tz, style = MaterialTheme.typography.bodySmall)
                                    }
                                    if (loc.isDefault) {
                                        Badge { Text("Default") }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun PreferenceRow(
    label: String,
    options: List<Pair<String, String>>,
    selected: String,
    onSelect: (String) -> Unit,
) {
    Column {
        Text(label, style = MaterialTheme.typography.labelMedium)
        Spacer(Modifier.height(4.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            options.forEach { (value, display) ->
                FilterChip(
                    selected = selected == value,
                    onClick = { onSelect(value) },
                    label = { Text(display) },
                )
            }
        }
    }
}
