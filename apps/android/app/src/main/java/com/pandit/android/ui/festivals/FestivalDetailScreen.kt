package com.pandit.android.ui.festivals

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ArrowBack
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel

// TODO(design): visual styling deferred to Aqualeo design system.

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FestivalDetailScreen(
    festivalId: String,
    onBack: () -> Unit,
    viewModel: FestivalDetailViewModel = hiltViewModel(),
) {
    LaunchedEffect(festivalId) { viewModel.load(festivalId) }
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(uiState.detail?.name ?: "") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Outlined.ArrowBack, contentDescription = "Back")
                    }
                },
            )
        }
    ) { paddingValues ->
        when {
            uiState.isLoading && uiState.detail == null -> {
                Box(
                    Modifier.fillMaxSize().padding(paddingValues),
                    contentAlignment = Alignment.Center,
                ) { CircularProgressIndicator() }
            }
            uiState.detail != null -> {
                val detail = uiState.detail!!
                Column(
                    modifier = Modifier
                        .padding(paddingValues)
                        .verticalScroll(rememberScrollState())
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    Text(detail.date, style = MaterialTheme.typography.bodySmall)
                    detail.description?.let { Text(it, style = MaterialTheme.typography.bodyMedium) }
                    detail.region?.let { Text("Region: $it", style = MaterialTheme.typography.bodySmall) }
                    if (detail.tags.isNotEmpty()) {
                        Text(detail.tags.joinToString(" · "), style = MaterialTheme.typography.labelSmall)
                    }
                    detail.body?.let {
                        Divider()
                        Text(it, style = MaterialTheme.typography.bodyMedium)
                    }
                    detail.puja?.let {
                        Divider()
                        Text("Puja", style = MaterialTheme.typography.titleSmall)
                        Text(it, style = MaterialTheme.typography.bodyMedium)
                    }
                    detail.katha?.let {
                        Divider()
                        Text("Katha", style = MaterialTheme.typography.titleSmall)
                        Text(it, style = MaterialTheme.typography.bodyMedium)
                    }
                }
            }
            else -> {
                Box(
                    Modifier.fillMaxSize().padding(paddingValues),
                    contentAlignment = Alignment.Center,
                ) { Text(uiState.error ?: "Error loading festival.") }
            }
        }
    }
}
