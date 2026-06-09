package com.pandit.android.ui.today

import android.content.Intent
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.BookmarkAdd
import androidx.compose.material.icons.outlined.BookmarkAdded
import androidx.compose.material.icons.outlined.Share
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.pandit.android.R
import com.pandit.android.data.api.*

// TODO(design): visual styling (colours, typography, spacing, icons) deferred to Aqualeo design system.

@Composable
fun TodayScreen(viewModel: TodayViewModel = hiltViewModel()) {
    val uiState by viewModel.uiState.collectAsState()
    val context = LocalContext.current

    if (uiState.explanation != null || uiState.explanationLoading) {
        ExplanationDialog(
            text = uiState.explanation,
            loading = uiState.explanationLoading,
            onDismiss = viewModel::dismissExplanation,
        )
    }

    Scaffold(
        topBar = {
            TodayTopBar(
                panchang = uiState.panchang,
                isBookmarked = uiState.isBookmarked,
                timeFormat = uiState.timeFormat,
                onBookmark = viewModel::toggleBookmark,
                onShare = {
                    uiState.panchang?.let { p ->
                        val shareText = buildShareText(p, uiState.timeFormat)
                        val intent = Intent(Intent.ACTION_SEND).apply {
                            type = "text/plain"
                            putExtra(Intent.EXTRA_TEXT, shareText)
                        }
                        context.startActivity(Intent.createChooser(intent, null))
                    }
                },
                onTimeFormatChange = viewModel::setTimeFormat,
            )
        }
    ) { paddingValues ->
        when {
            uiState.isLoading && uiState.panchang == null -> {
                Box(
                    Modifier
                        .fillMaxSize()
                        .padding(paddingValues),
                    contentAlignment = Alignment.Center,
                ) {
                    CircularProgressIndicator(
                        modifier = Modifier.semantics {
                            contentDescription = context.getString(R.string.loading)
                        }
                    )
                }
            }
            uiState.panchang != null -> {
                TodayContent(
                    panchang = uiState.panchang!!,
                    timeFormat = uiState.timeFormat,
                    isOffline = uiState.isOffline,
                    onExplain = viewModel::requestExplanation,
                    modifier = Modifier.padding(paddingValues),
                )
            }
            else -> {
                Box(
                    Modifier
                        .fillMaxSize()
                        .padding(paddingValues),
                    contentAlignment = Alignment.Center,
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(stringResource(R.string.error_generic))
                        Spacer(Modifier.height(16.dp))
                        Button(onClick = viewModel::load) { Text("Retry") }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun TodayTopBar(
    panchang: DailyPanchangViewDto?,
    isBookmarked: Boolean,
    timeFormat: String,
    onBookmark: () -> Unit,
    onShare: () -> Unit,
    onTimeFormatChange: (String) -> Unit,
) {
    TopAppBar(
        title = {
            Column {
                panchang?.location?.let { Text(text = it, style = MaterialTheme.typography.titleMedium) }
                panchang?.date?.let { Text(text = it, style = MaterialTheme.typography.bodySmall) }
            }
        },
        actions = {
            // 12h / 24h / 24+ toggle
            TimeFormatToggle(
                current = timeFormat,
                onChange = onTimeFormatChange,
            )
            IconButton(
                onClick = onBookmark,
                modifier = Modifier.semantics {
                    contentDescription = if (isBookmarked) "Remove bookmark" else "Bookmark this day"
                },
            ) {
                Icon(
                    imageVector = if (isBookmarked) Icons.Outlined.BookmarkAdded else Icons.Outlined.BookmarkAdd,
                    contentDescription = null,
                )
            }
            IconButton(
                onClick = onShare,
                modifier = Modifier.semantics { contentDescription = "Share" },
            ) {
                Icon(Icons.Outlined.Share, contentDescription = null)
            }
        }
    )
}

@Composable
private fun TimeFormatToggle(current: String, onChange: (String) -> Unit) {
    val formats = listOf("12h", "24h", "24plus")
    val labels = listOf(
        stringResource(R.string.time_format_12h),
        stringResource(R.string.time_format_24h),
        stringResource(R.string.time_format_24plus),
    )
    Row(
        modifier = Modifier.semantics(mergeDescendants = true) {
            contentDescription = "Time format: $current"
        }
    ) {
        formats.forEachIndexed { i, fmt ->
            TextButton(
                onClick = { onChange(fmt) },
                colors = if (current == fmt)
                    ButtonDefaults.textButtonColors(contentColor = MaterialTheme.colorScheme.primary)
                else
                    ButtonDefaults.textButtonColors(contentColor = MaterialTheme.colorScheme.onSurface),
            ) {
                Text(labels[i], style = MaterialTheme.typography.labelSmall)
            }
        }
    }
}

@Composable
private fun TodayContent(
    panchang: DailyPanchangViewDto,
    timeFormat: String,
    isOffline: Boolean,
    onExplain: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    LazyColumn(modifier = modifier.fillMaxSize(), contentPadding = PaddingValues(16.dp)) {
        // Offline banner
        if (isOffline) {
            item {
                OfflineBanner()
                Spacer(Modifier.height(8.dp))
            }
        }

        // Sun/moon times
        item {
            SectionHeader("Sun & Moon")
            TimeRow("Sunrise", panchang.sunrise.display(timeFormat))
            TimeRow("Sunset", panchang.sunset.display(timeFormat))
            panchang.moonrise?.let { TimeRow("Moonrise", it.display(timeFormat)) }
            panchang.moonset?.let { TimeRow("Moonset", it.display(timeFormat)) }
            Spacer(Modifier.height(16.dp))
        }

        // Core Panchang elements (tap to explain)
        item {
            SectionHeader("Panchang")
        }
        items(
            listOf(panchang.tithi, panchang.nakshatra, panchang.yoga, panchang.karana, panchang.vara)
        ) { element ->
            PanchangElementRow(
                element = element,
                timeFormat = timeFormat,
                onExplain = { element.explanationKey?.let { onExplain(it) } },
            )
        }

        item { Spacer(Modifier.height(16.dp)) }

        // Muhurat windows
        if (panchang.muhurats.isNotEmpty()) {
            item { SectionHeader(stringResource(R.string.today_muhurat)) }
            items(panchang.muhurats) { m ->
                MuhuratRow(m, timeFormat)
            }
            item { Spacer(Modifier.height(16.dp)) }
        }

        // Festivals / Vrats
        if (panchang.festivals.isNotEmpty()) {
            item { SectionHeader("Festivals & Vrats") }
            items(panchang.festivals) { f ->
                FestivalChip(f)
            }
            item { Spacer(Modifier.height(16.dp)) }
        }

        // Advisory
        item {
            SectionHeader("Advisory")
            AdvisorySection(panchang.advisory)
            Spacer(Modifier.height(16.dp))
        }

        // Highlights
        if (panchang.highlights.isNotEmpty()) {
            item { SectionHeader(stringResource(R.string.today_highlights)) }
            items(panchang.highlights) { h ->
                HighlightRow(h)
            }
            item { Spacer(Modifier.height(16.dp)) }
        }

        // Dharma card
        panchang.dharmaCard?.let { card ->
            item {
                DharmaCardSection(card)
                Spacer(Modifier.height(16.dp))
            }
        }
    }
}

@Composable
private fun SectionHeader(title: String) {
    Text(
        text = title,
        style = MaterialTheme.typography.titleMedium,
        modifier = Modifier.padding(vertical = 4.dp),
    )
}

@Composable
private fun TimeRow(label: String, value: String) {
    Row(Modifier.fillMaxWidth().padding(vertical = 2.dp)) {
        Text(label, modifier = Modifier.weight(1f), style = MaterialTheme.typography.bodyMedium)
        Text(value, style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun PanchangElementRow(
    element: PanchangElementDto,
    timeFormat: String,
    onExplain: () -> Unit,
) {
    val cdExplain = stringResource(R.string.cd_explain) + ": ${element.label}"
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClickLabel = cdExplain, onClick = onExplain)
            .padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(element.label, style = MaterialTheme.typography.labelMedium)
            Text(element.value, style = MaterialTheme.typography.bodyMedium)
        }
        val span = buildTimeSpan(element, timeFormat)
        if (span != null) {
            Text(span, style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
private fun MuhuratRow(m: MuhuratWindowDto, timeFormat: String) {
    Row(
        Modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp)
            .semantics {
                contentDescription =
                    "${m.name}: ${m.start.display(timeFormat)} to ${m.end.display(timeFormat)}, " +
                    if (m.isAuspicious) "auspicious" else "inauspicious"
            }
    ) {
        Text(m.name, Modifier.weight(1f), style = MaterialTheme.typography.bodyMedium)
        Text(
            "${m.start.display(timeFormat)} – ${m.end.display(timeFormat)}",
            style = MaterialTheme.typography.bodySmall,
        )
    }
}

@Composable
private fun FestivalChip(festival: FestivalDto) {
    SuggestionChip(
        onClick = {},
        label = { Text(festival.name) },
        modifier = Modifier.padding(end = 4.dp, bottom = 4.dp),
    )
}

@Composable
private fun AdvisorySection(advisory: AdvisoryDto) {
    if (advisory.goodFor.isNotEmpty()) {
        Text(
            stringResource(R.string.today_good_for),
            style = MaterialTheme.typography.labelMedium,
        )
        Text(advisory.goodFor.joinToString(" · "), style = MaterialTheme.typography.bodySmall)
    }
    if (advisory.avoid.isNotEmpty()) {
        Spacer(Modifier.height(4.dp))
        Text(
            stringResource(R.string.today_avoid),
            style = MaterialTheme.typography.labelMedium,
        )
        Text(advisory.avoid.joinToString(" · "), style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
private fun HighlightRow(h: DailyHighlightDto) {
    Row(Modifier.fillMaxWidth().padding(vertical = 2.dp)) {
        Text(h.label, Modifier.weight(1f), style = MaterialTheme.typography.bodySmall)
        Text(h.value, style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
private fun DharmaCardSection(card: DharmaCardDto) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp)) {
            Text(
                stringResource(R.string.today_dharma_card),
                style = MaterialTheme.typography.labelMedium,
            )
            Spacer(Modifier.height(8.dp))
            Text(card.text, style = MaterialTheme.typography.bodyMedium)
            card.source?.let { src ->
                Spacer(Modifier.height(4.dp))
                Text("— $src", style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
private fun OfflineBanner() {
    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Text(
            stringResource(R.string.offline_banner),
            modifier = Modifier.padding(12.dp),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onErrorContainer,
        )
    }
}

@Composable
private fun ExplanationDialog(
    text: String?,
    loading: Boolean,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        confirmButton = { TextButton(onClick = onDismiss) { Text("Close") } },
        text = {
            if (loading) {
                CircularProgressIndicator()
            } else {
                Text(text ?: "")
            }
        }
    )
}

private fun TimeValueDto.display(format: String): String = when (format) {
    "24h" -> hour24
    "24plus" -> hour24Plus
    else -> hour12
}

private fun buildTimeSpan(element: PanchangElementDto, format: String): String? {
    val start = element.startTime?.display(format) ?: return null
    val end = element.endTime?.display(format)
    return if (end != null) "$start – $end" else start
}

private fun buildShareText(p: DailyPanchangViewDto, timeFormat: String): String = buildString {
    appendLine("${p.location} — ${p.date}")
    appendLine("Tithi: ${p.tithi.value}")
    appendLine("Nakshatra: ${p.nakshatra.value}")
    appendLine("Yoga: ${p.yoga.value}")
    appendLine("Sunrise: ${p.sunrise.display(timeFormat)} | Sunset: ${p.sunset.display(timeFormat)}")
    if (p.festivals.isNotEmpty()) {
        appendLine("Festivals: ${p.festivals.joinToString(", ") { it.name }}")
    }
    appendLine("— via The Pandit")
}
