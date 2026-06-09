package com.pandit.android.ui.calendar

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ChevronLeft
import androidx.compose.material.icons.outlined.ChevronRight
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.pandit.android.R
import com.pandit.android.data.api.DailyPanchangDto
import com.pandit.android.data.api.NoteDto
import java.time.LocalDate
import java.time.YearMonth
import java.time.format.TextStyle
import java.util.Locale

// TODO(design): visual styling deferred to Aqualeo design system.

@Composable
fun CalendarScreen(viewModel: CalendarViewModel = hiltViewModel()) {
    val uiState by viewModel.uiState.collectAsState()

    if (uiState.showAddNote) {
        AddNoteDialog(
            onConfirm = { viewModel.addNote(it) },
            onDismiss = { viewModel.showAddNote(false) },
        )
    }

    if (uiState.showAddReminder) {
        AddReminderDialog(
            onConfirm = { title, type, value, advance ->
                viewModel.addReminder(title, type, value, advance)
            },
            onDismiss = { viewModel.showAddReminder(false) },
        )
    }

    Column(Modifier.fillMaxSize()) {
        MonthHeader(
            yearMonth = uiState.yearMonth,
            onPrev = viewModel::previousMonth,
            onNext = viewModel::nextMonth,
        )

        MonthGrid(
            yearMonth = uiState.yearMonth,
            selectedDate = uiState.selectedDate,
            monthData = uiState.monthData,
            onSelectDate = viewModel::selectDate,
        )

        Divider()

        if (uiState.isLoadingDay) {
            Box(Modifier.fillMaxWidth().height(120.dp), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
        } else {
            DayDetail(
                date = uiState.selectedDate,
                dayData = uiState.selectedDayData,
                notes = uiState.notes,
                timeFormat = uiState.timeFormat,
                onAddNote = { viewModel.showAddNote(true) },
                onAddReminder = { viewModel.showAddReminder(true) },
                onBookmark = viewModel::toggleBookmark,
            )
        }
    }
}

@Composable
private fun MonthHeader(
    yearMonth: YearMonth,
    onPrev: () -> Unit,
    onNext: () -> Unit,
) {
    Row(
        Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        IconButton(
            onClick = onPrev,
            modifier = Modifier.semantics { contentDescription = "Previous month" },
        ) { Icon(Icons.Outlined.ChevronLeft, null) }

        Text(
            text = "${yearMonth.month.getDisplayName(TextStyle.FULL, Locale.getDefault())} ${yearMonth.year}",
            style = MaterialTheme.typography.titleMedium,
        )

        IconButton(
            onClick = onNext,
            modifier = Modifier.semantics { contentDescription = "Next month" },
        ) { Icon(Icons.Outlined.ChevronRight, null) }
    }
}

@Composable
private fun MonthGrid(
    yearMonth: YearMonth,
    selectedDate: LocalDate,
    monthData: com.pandit.android.data.api.MonthCalendarDto?,
    onSelectDate: (LocalDate) -> Unit,
) {
    val firstDay = yearMonth.atDay(1).dayOfWeek.value % 7 // 0=Sun
    val daysInMonth = yearMonth.lengthOfMonth()

    // Day-of-week headers
    val dowLabels = listOf("Su", "Mo", "Tu", "We", "Th", "Fr", "Sa")
    Row(Modifier.fillMaxWidth().padding(horizontal = 8.dp)) {
        dowLabels.forEach { label ->
            Text(
                text = label,
                modifier = Modifier.weight(1f),
                style = MaterialTheme.typography.labelSmall,
                textAlign = androidx.compose.ui.text.style.TextAlign.Center,
            )
        }
    }

    val dayDataMap = monthData?.days?.associateBy { it.date } ?: emptyMap()

    LazyVerticalGrid(
        columns = GridCells.Fixed(7),
        modifier = Modifier.fillMaxWidth().height(300.dp),
        contentPadding = PaddingValues(horizontal = 8.dp),
    ) {
        // Empty cells before first day
        items(firstDay) { Box(Modifier.aspectRatio(1f)) }

        items(daysInMonth) { dayIndex ->
            val date = yearMonth.atDay(dayIndex + 1)
            val dateStr = date.toString()
            val dayData = dayDataMap[dateStr]
            val isSelected = date == selectedDate

            DayCell(
                day = dayIndex + 1,
                isSelected = isSelected,
                tithi = dayData?.tithi?.firstOrNull()?.name,
                hasFestival = monthData?.days?.find { it.date == dateStr }
                    ?.let { false } ?: false, // festivals are on today view; placeholder
                onClick = { onSelectDate(date) },
                contentDesc = "${date.dayOfWeek.getDisplayName(TextStyle.SHORT, Locale.getDefault())}, " +
                    "${date.month.getDisplayName(TextStyle.SHORT, Locale.getDefault())} ${dayIndex + 1}" +
                    (dayData?.tithi?.firstOrNull()?.name?.let { ", $it" } ?: ""),
            )
        }
    }
}

@Composable
private fun DayCell(
    day: Int,
    isSelected: Boolean,
    tithi: String?,
    hasFestival: Boolean,
    onClick: () -> Unit,
    contentDesc: String,
) {
    Box(
        modifier = Modifier
            .aspectRatio(1f)
            .padding(2.dp)
            .clickable(onClickLabel = contentDesc, onClick = onClick)
            .semantics { contentDescription = contentDesc },
        contentAlignment = Alignment.Center,
    ) {
        // TODO(design): selection indicator, festival dot, appearance via design tokens
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            if (isSelected) {
                Surface(
                    shape = MaterialTheme.shapes.extraLarge,
                    color = MaterialTheme.colorScheme.primary,
                ) {
                    Text(
                        "$day",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onPrimary,
                        modifier = Modifier.padding(4.dp),
                    )
                }
            } else {
                Text("$day", style = MaterialTheme.typography.bodySmall)
            }
            tithi?.let {
                Text(
                    it.take(4),
                    style = MaterialTheme.typography.labelSmall,
                    maxLines = 1,
                )
            }
        }
    }
}

@Composable
private fun DayDetail(
    date: LocalDate,
    dayData: DailyPanchangDto?,
    notes: List<NoteDto>,
    timeFormat: String,
    onAddNote: () -> Unit,
    onAddReminder: () -> Unit,
    onBookmark: () -> Unit,
) {
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(16.dp)) {
        dayData?.let { data ->
            item {
                Text(date.toString(), style = MaterialTheme.typography.titleSmall)
                Text("Tithi: ${data.tithi.firstOrNull()?.name ?: "—"}", style = MaterialTheme.typography.bodySmall)
                Text("Nakshatra: ${data.nakshatra.firstOrNull()?.name ?: "—"}", style = MaterialTheme.typography.bodySmall)
                Text(
                    "Sunrise: ${data.dayEvents.sunrise.let { if (timeFormat == "24h") it.hour24 else it.hour12 }}",
                    style = MaterialTheme.typography.bodySmall,
                )
                Spacer(Modifier.height(8.dp))
            }
        }

        item {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = onAddNote) { Text(stringResource(R.string.calendar_add_note)) }
                OutlinedButton(onClick = onAddReminder) { Text(stringResource(R.string.calendar_add_reminder)) }
                OutlinedButton(onClick = onBookmark) { Text(stringResource(R.string.calendar_bookmark_day)) }
            }
            Spacer(Modifier.height(8.dp))
        }

        if (notes.isNotEmpty()) {
            item { Text(stringResource(R.string.calendar_notes), style = MaterialTheme.typography.labelMedium) }
            items(notes) { note ->
                Text("• ${note.body}", style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(vertical = 2.dp))
            }
        }
    }
}

@Composable
private fun AddNoteDialog(onConfirm: (String) -> Unit, onDismiss: () -> Unit) {
    var text by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.calendar_add_note)) },
        text = {
            OutlinedTextField(
                value = text,
                onValueChange = { text = it },
                modifier = Modifier.fillMaxWidth(),
                placeholder = { Text("Note…") },
            )
        },
        confirmButton = {
            TextButton(onClick = { if (text.isNotBlank()) onConfirm(text) }, enabled = text.isNotBlank()) {
                Text("Save")
            }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    )
}

@Composable
private fun AddReminderDialog(
    onConfirm: (String, String, String, Int) -> Unit,
    onDismiss: () -> Unit,
) {
    var title by remember { mutableStateOf("") }
    var triggerType by remember { mutableStateOf("gregorian") }
    var triggerValue by remember { mutableStateOf("") }
    var advance by remember { mutableStateOf("30") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.calendar_add_reminder)) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = title,
                    onValueChange = { title = it },
                    label = { Text("Title") },
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = triggerValue,
                    onValueChange = { triggerValue = it },
                    label = { Text("Trigger value (e.g. date or tithi name)") },
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = advance,
                    onValueChange = { advance = it },
                    label = { Text("Advance minutes") },
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        },
        confirmButton = {
            TextButton(
                onClick = {
                    onConfirm(title, triggerType, triggerValue, advance.toIntOrNull() ?: 30)
                },
                enabled = title.isNotBlank() && triggerValue.isNotBlank(),
            ) { Text("Save") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    )
}
