// TODO(design): all visual values via DesignTokens — no colour/font decisions here.
import SwiftUI
import SwiftData

struct CalendarView: View {
    @Environment(\.modelContext) private var context
    @Environment(\.designTokens) private var tokens
    @Bindable var viewModel: CalendarViewModel

    @State private var showAddNote = false
    @State private var showAddReminder = false
    @State private var noteText = ""

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                monthHeader
                weekdayHeader
                monthGrid
                Divider()
                dayDetailPanel
            }
            .navigationTitle("Calendar")
            .toolbar { toolbarContent }
        }
        .task { await viewModel.loadMonth(context: context) }
        .onChange(of: viewModel.currentMonth) { _, _ in
            Task { await viewModel.loadMonth(context: context) }
        }
        .sheet(isPresented: $showAddNote) { addNoteSheet }
        .sheet(isPresented: $showAddReminder) { addReminderSheet }
    }

    // MARK: - Month navigation header

    private var monthHeader: some View {
        HStack {
            Button {
                viewModel.selectedDate = Calendar.current.date(
                    byAdding: .month, value: -1, to: viewModel.selectedDate)!
            } label: {
                Image(systemName: "chevron.left")
            }
            .accessibilityLabel("Previous month")

            Spacer()
            Text(monthTitle).font(.headline)
                .accessibilityLabel("Month: \(monthTitle)")
            Spacer()

            Button {
                viewModel.selectedDate = Calendar.current.date(
                    byAdding: .month, value: 1, to: viewModel.selectedDate)!
            } label: {
                Image(systemName: "chevron.right")
            }
            .accessibilityLabel("Next month")
        }
        .padding(.horizontal)
        .padding(.vertical, 8)
    }

    // MARK: - Weekday header

    private var weekdayHeader: some View {
        let symbols = Calendar.current.veryShortWeekdaySymbols
        return HStack {
            ForEach(symbols, id: \.self) { sym in
                Text(sym)
                    .font(.caption2)
                    .frame(maxWidth: .infinity)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.horizontal, 4)
    }

    // MARK: - Month grid

    private var monthGrid: some View {
        let days = daysInGrid()
        return LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 0), count: 7), spacing: 4) {
            ForEach(days, id: \.self) { date in
                if let date {
                    DayCell(
                        date: date,
                        dayData: viewModel.dayData(for: date),
                        isSelected: Calendar.current.isDate(date, inSameDayAs: viewModel.selectedDate),
                        isToday: Calendar.current.isDateInToday(date)
                    ) {
                        Task { await viewModel.selectDay(date, context: context) }
                    }
                } else {
                    Color.clear.frame(height: 52)
                }
            }
        }
        .padding(.horizontal, 4)
        .overlay {
            if viewModel.isLoadingMonth {
                ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(.ultraThinMaterial)
            }
        }
    }

    // MARK: - Day detail panel

    @ViewBuilder
    private var dayDetailPanel: some View {
        ScrollView {
            if let p = viewModel.selectedDayPanchang {
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        VStack(alignment: .leading) {
                            Text(p.date).font(.subheadline).foregroundStyle(.secondary)
                            Text("\(p.tithi.first?.name ?? "") · \(p.nakshatra.first?.name ?? "")")
                                .font(.headline)
                        }
                        Spacer()
                    }

                    // Notes section
                    notesList

                    // Reminders section
                    remindersList
                }
                .padding()
            } else if viewModel.isLoadingDay {
                ProgressView("Loading…").padding()
            }
        }
        .frame(maxHeight: 300)
    }

    @ViewBuilder
    private var notesList: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text("Notes").font(.subheadline).bold()
                Spacer()
                Button { showAddNote = true } label: {
                    Image(systemName: "plus.circle")
                }
                .accessibilityLabel("Add note")
            }
            if viewModel.notes.isEmpty {
                Text("No notes").font(.caption).foregroundStyle(.secondary)
            }
            ForEach(viewModel.notes, id: \.localId) { note in
                HStack {
                    Text(note.body).font(.footnote)
                    Spacer()
                    Button {
                        viewModel.deleteNote(note, context: context)
                    } label: {
                        Image(systemName: "trash").font(.caption)
                    }
                    .accessibilityLabel("Delete note")
                }
            }
        }
    }

    @ViewBuilder
    private var remindersList: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text("Reminders").font(.subheadline).bold()
                Spacer()
                Button { showAddReminder = true } label: {
                    Image(systemName: "plus.circle")
                }
                .accessibilityLabel("Add reminder")
            }
            if viewModel.reminders.isEmpty {
                Text("No reminders").font(.caption).foregroundStyle(.secondary)
            }
            ForEach(viewModel.reminders, id: \.localId) { r in
                Text(r.title).font(.footnote)
            }
        }
    }

    // MARK: - Sheets

    private var addNoteSheet: some View {
        NavigationStack {
            Form {
                TextField("Note", text: $noteText, axis: .vertical)
                    .lineLimit(4...)
                    .accessibilityLabel("Note text")
            }
            .navigationTitle("Add Note")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { showAddNote = false }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        viewModel.addNote(body: noteText, context: context)
                        noteText = ""
                        showAddNote = false
                    }
                    .disabled(noteText.trimmingCharacters(in: .whitespaces).isEmpty)
                }
            }
        }
        .presentationDetents([.medium])
    }

    private var addReminderSheet: some View {
        AddReminderView { title, type, value, advance in
            viewModel.addReminder(title: title, triggerType: type,
                                  triggerValue: value, advanceMinutes: advance, context: context)
            showAddReminder = false
        } onCancel: { showAddReminder = false }
    }

    // MARK: - Toolbar

    @ToolbarContentBuilder
    private var toolbarContent: some ToolbarContent {
        ToolbarItem(placement: .navigationBarTrailing) {
            Button("Today") {
                Task { await viewModel.selectDay(Date(), context: context) }
            }
            .accessibilityLabel("Jump to today")
        }
    }

    // MARK: - Helpers

    private var monthTitle: String {
        let fmt = DateFormatter()
        fmt.dateFormat = "MMMM yyyy"
        return fmt.string(from: viewModel.selectedDate)
    }

    private func daysInGrid() -> [Date?] {
        let cal = Calendar.current
        let comps = cal.dateComponents([.year, .month], from: viewModel.selectedDate)
        guard let firstDay = cal.date(from: comps),
              let range = cal.range(of: .day, in: .month, for: firstDay) else { return [] }
        let weekdayOffset = (cal.component(.weekday, from: firstDay) - cal.firstWeekday + 7) % 7
        var result: [Date?] = Array(repeating: nil, count: weekdayOffset)
        for day in range {
            result.append(cal.date(byAdding: .day, value: day - 1, to: firstDay))
        }
        return result
    }
}

// MARK: - Day cell

private struct DayCell: View {
    let date: Date
    let dayData: DailyPanchang?
    let isSelected: Bool
    let isToday: Bool
    let onTap: () -> Void

    private var dayNumber: String {
        "\(Calendar.current.component(.day, from: date))"
    }

    var body: some View {
        Button(action: onTap) {
            VStack(spacing: 2) {
                Text(dayNumber)
                    .font(isToday ? .subheadline.bold() : .subheadline)
                    .frame(width: 32, height: 32)
                    // TODO(design): selection/today highlight via DesignTokens
                    .background(isSelected ? Color.accentColor.opacity(0.2) : Color.clear)
                    .clipShape(Circle())

                if let d = dayData {
                    Text(d.tithi.first?.name.prefix(3) ?? "")
                        .font(.system(size: 8))
                        .foregroundStyle(.secondary)
                        .lineLimit(1)

                    // Moon phase placeholder — TODO(data): derive from moon longitude
                    Circle()
                        .fill(Color.secondary.opacity(0.3))
                        .frame(width: 4, height: 4)
                }
            }
            .frame(height: 52)
        }
        .buttonStyle(.plain)
        .accessibilityLabel("\(dayNumber) \(dayData?.tithi.first?.name ?? "")")
        .accessibilityAddTraits(isSelected ? .isSelected : [])
        .accessibilityAddTraits(isToday ? .isHeader : [])
    }
}

// MARK: - Add Reminder view

private struct AddReminderView: View {
    @State private var title = ""
    @State private var triggerType = "gregorian"
    @State private var triggerValue = ""
    @State private var advance = 0

    let onSave: (String, String, String, Int) -> Void
    let onCancel: () -> Void

    var body: some View {
        NavigationStack {
            Form {
                TextField("Title", text: $title).accessibilityLabel("Reminder title")
                Picker("Type", selection: $triggerType) {
                    Text("Gregorian date").tag("gregorian")
                    Text("Tithi").tag("tithi")
                    Text("Nakshatra").tag("nakshatra")
                }
                TextField("Value (e.g. 2026-01-14 or Ekadashi)", text: $triggerValue)
                    .accessibilityLabel("Trigger value")
                Stepper("Advance: \(advance) min", value: $advance, in: 0...1440, step: 15)
                    .accessibilityLabel("Advance notice: \(advance) minutes")
            }
            .navigationTitle("Add Reminder")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel", action: onCancel)
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") { onSave(title, triggerType, triggerValue, advance) }
                        .disabled(title.isEmpty || triggerValue.isEmpty)
                }
            }
        }
        .presentationDetents([.medium])
    }
}
