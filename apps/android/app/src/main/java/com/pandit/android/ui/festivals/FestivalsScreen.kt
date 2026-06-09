package com.pandit.android.ui.festivals

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.pandit.android.data.api.FestivalDto

// TODO(design): visual styling deferred to Aqualeo design system.

@Composable
fun FestivalsScreen(
    onFestivalClick: (String) -> Unit,
    viewModel: FestivalsViewModel = hiltViewModel(),
) {
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = {
            @OptIn(ExperimentalMaterial3Api::class)
            TopAppBar(title = { Text("Festivals & Vrats") })
        }
    ) { paddingValues ->
        when {
            uiState.isLoading && uiState.festivals.isEmpty() -> {
                Box(
                    Modifier.fillMaxSize().padding(paddingValues),
                    contentAlignment = Alignment.Center,
                ) { CircularProgressIndicator() }
            }
            uiState.festivals.isEmpty() -> {
                Box(
                    Modifier.fillMaxSize().padding(paddingValues),
                    contentAlignment = Alignment.Center,
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text("No festivals found.")
                        Spacer(Modifier.height(16.dp))
                        Button(onClick = viewModel::refresh) { Text("Retry") }
                    }
                }
            }
            else -> {
                LazyColumn(
                    modifier = Modifier.padding(paddingValues),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    if (uiState.isOffline) {
                        item {
                            Card(
                                colors = CardDefaults.cardColors(
                                    containerColor = MaterialTheme.colorScheme.errorContainer
                                )
                            ) {
                                Text(
                                    "Showing cached festivals.",
                                    modifier = Modifier.padding(12.dp),
                                    style = MaterialTheme.typography.bodySmall,
                                )
                            }
                        }
                    }
                    items(uiState.festivals, key = { it.id }) { festival ->
                        FestivalListItem(festival = festival, onClick = { onFestivalClick(festival.id) })
                    }
                }
            }
        }
    }
}

@Composable
private fun FestivalListItem(festival: FestivalDto, onClick: () -> Unit) {
    val cd = "${festival.name}, ${festival.date}"
    ListItem(
        headlineContent = { Text(festival.name) },
        supportingContent = {
            Column {
                Text(festival.date, style = MaterialTheme.typography.bodySmall)
                festival.description?.let {
                    Text(it, style = MaterialTheme.typography.bodySmall, maxLines = 2)
                }
                if (festival.tags.isNotEmpty()) {
                    Text(
                        festival.tags.joinToString(" · "),
                        style = MaterialTheme.typography.labelSmall,
                    )
                }
            }
        },
        modifier = Modifier
            .clickable(onClickLabel = cd, onClick = onClick)
            .semantics { contentDescription = cd },
    )
    HorizontalDivider()
}
