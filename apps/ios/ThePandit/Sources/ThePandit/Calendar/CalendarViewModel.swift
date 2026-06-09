import Foundation
import SwiftData
import CoreLocation

@MainActor
@Observable
final class CalendarViewModel {
    var selectedDate: Date = Date()
    var monthData: MonthCalendar?
    var selectedDayPanchang: DailyPanchang?
    var notes: [LocalNote] = []
    var reminders: [LocalReminder] = []

    var isLoadingMonth = false
    var isLoadingDay = false
    var error: String?

    var location: CLLocation?
    var timezone: TimeZone = .current

    private let api = APIClient.shared
    private let cache = OfflineCache.shared

    var currentYear: Int { Calendar.current.component(.year, from: selectedDate) }
    var currentMonth: Int { Calendar.current.component(.month, from: selectedDate) }

    func loadMonth(context: ModelContext) async {
        guard let location else { return }
        isLoadingMonth = true
        let lat = location.coordinate.latitude
        let lon = location.coordinate.longitude
        let tz = timezone.identifier

        do {
            let result = try await api.monthCalendar(year: currentYear, month: currentMonth,
                                                     lat: lat, lon: lon, tz: tz)
            monthData = result
            // Cache each day
            for day in result.days {
                try? await cache.storePanchang(day, context: context)
            }
        } catch {
            self.error = (error as? LocalizedError)?.errorDescription
        }
        isLoadingMonth = false
    }

    func selectDay(_ date: Date, context: ModelContext) async {
        selectedDate = date
        isLoadingDay = true

        let dateStr = formattedDate(date)
        guard let location else { isLoadingDay = false; return }
        let lat = location.coordinate.latitude
        let lon = location.coordinate.longitude
        let tz = timezone.identifier

        // Try cache first for fast response
        if let cached = try? await cache.fetchPanchang(date: dateStr, lat: lat, lon: lon, tz: tz,
                                                       ayanamsa: "lahiri", monthScheme: "amanta",
                                                       context: context) {
            selectedDayPanchang = cached
        }

        // Then refresh from API
        do {
            let fresh = try await api.dailyPanchang(date: dateStr, lat: lat, lon: lon, tz: tz)
            selectedDayPanchang = fresh
            try? await cache.storePanchang(fresh, context: context)
        } catch {
            if selectedDayPanchang == nil {
                self.error = (error as? LocalizedError)?.errorDescription
            }
        }

        loadLocalNotes(for: dateStr, context: context)
        loadLocalReminders(context: context)
        isLoadingDay = false
    }

    func addNote(body: String, context: ModelContext) {
        let note = LocalNote(date: formattedDate(selectedDate), body: body)
        context.insert(note)
        try? context.save()
        loadLocalNotes(for: formattedDate(selectedDate), context: context)
        // TODO(sync): sync to API in background
    }

    func deleteNote(_ note: LocalNote, context: ModelContext) {
        context.delete(note)
        try? context.save()
        loadLocalNotes(for: formattedDate(selectedDate), context: context)
    }

    func addReminder(title: String, triggerType: String, triggerValue: String, advanceMinutes: Int, context: ModelContext) {
        let reminder = LocalReminder(title: title, triggerType: triggerType,
                                     triggerValue: triggerValue, advanceMinutes: advanceMinutes)
        context.insert(reminder)
        try? context.save()
        loadLocalReminders(context: context)
    }

    // MARK: - Calendar markers

    func dayData(for date: Date) -> DailyPanchang? {
        let str = formattedDate(date)
        return monthData?.days.first { $0.date == str }
    }

    // MARK: - Private

    private func loadLocalNotes(for date: String, context: ModelContext) {
        let descriptor = FetchDescriptor<LocalNote>(
            predicate: #Predicate { $0.date == date && $0.syncState != "pending_delete" }
        )
        notes = (try? context.fetch(descriptor)) ?? []
    }

    private func loadLocalReminders(context: ModelContext) {
        let descriptor = FetchDescriptor<LocalReminder>(
            predicate: #Predicate { $0.syncState != "pending_delete" }
        )
        reminders = (try? context.fetch(descriptor)) ?? []
    }

    private func formattedDate(_ date: Date) -> String {
        let fmt = DateFormatter()
        fmt.dateFormat = "yyyy-MM-dd"
        return fmt.string(from: date)
    }
}
