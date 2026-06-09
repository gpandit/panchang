import XCTest
import SwiftData
@testable import ThePandit

final class OfflineCacheTests: XCTestCase {

    private func makeContainer() throws -> ModelContainer {
        let config = ModelConfiguration(isStoredInMemoryOnly: true)
        return try ModelContainer(for: CachedDay.self, CachedFestival.self,
                                  LocalNote.self, LocalReminder.self,
                                  configurations: config)
    }

    private func makePanchang(date: String = "2026-01-14") -> DailyPanchang {
        let tv = TimeValue(iso: "", hour24: "07:15", hour12: "7:15 AM", hour24Plus: "07:15")
        return DailyPanchang(
            date: date, lat: 28.6, lon: 77.2, tz: "Asia/Kolkata",
            ayanamsa: "lahiri", monthScheme: "amanta",
            sunLongitude: 293.5, moonLongitude: 120.3, ayanamsaValue: 24.1,
            tithi: [AngaSpan(index: 0, name: "Chaturdashi", start: nil, end: nil)],
            nakshatra: [AngaSpan(index: 0, name: "Uttara Phalguni", start: nil, end: nil)],
            yoga: [AngaSpan(index: 0, name: "Shubha", start: nil, end: nil)],
            karana: [AngaSpan(index: 0, name: "Vishti", start: nil, end: nil)],
            vara: AngaSpan(index: 3, name: "Budhavara", start: nil, end: nil),
            dayEvents: DayEvents(sunrise: tv, sunset: tv, moonrise: nil, moonset: nil),
            muhurat: [], choghadiya: [], hora: [],
            calendrical: Calendrical(
                shakaSamvat: 1948, vikramSamvat: 2083, gujaratiSamvat: 2082,
                samvatsara: "Shobhana", ritu: "Shishira", ayana: "Uttarayana",
                lunarMonth: "Pausha", isAdhikaMonth: false, isKshayaMonth: false,
                paksha: "Krishna", moonRashi: "Simha", sunRashi: "Dhanu"
            ),
            cached: false
        )
    }

    @MainActor
    func test_store_and_fetch_roundtrip() async throws {
        let container = try makeContainer()
        let cache = OfflineCache()
        let p = makePanchang()

        try await cache.storePanchang(p, context: container.mainContext)
        let fetched = try await cache.fetchPanchang(
            date: p.date, lat: p.lat, lon: p.lon, tz: p.tz,
            ayanamsa: p.ayanamsa, monthScheme: p.monthScheme,
            context: container.mainContext
        )

        XCTAssertNotNil(fetched)
        XCTAssertEqual(fetched?.date, p.date)
        XCTAssertEqual(fetched?.tithi.first?.name, "Chaturdashi")
    }

    @MainActor
    func test_fetch_missingKey_returnsNil() async throws {
        let container = try makeContainer()
        let cache = OfflineCache()

        let fetched = try await cache.fetchPanchang(
            date: "1999-01-01", lat: 0, lon: 0, tz: "UTC",
            ayanamsa: "lahiri", monthScheme: "amanta",
            context: container.mainContext
        )
        XCTAssertNil(fetched)
    }

    @MainActor
    func test_overwrite_updates_cachedAt() async throws {
        let container = try makeContainer()
        let cache = OfflineCache()
        let p = makePanchang()

        try await cache.storePanchang(p, context: container.mainContext)
        let before = Date()

        // Wait a tiny bit then overwrite
        try await Task.sleep(for: .milliseconds(10))
        try await cache.storePanchang(p, context: container.mainContext)

        let descriptor = FetchDescriptor<CachedDay>()
        let records = try container.mainContext.fetch(descriptor)
        XCTAssertEqual(records.count, 1)  // no duplicate
        XCTAssertGreaterThanOrEqual(records[0].cachedAt, before)
    }

    @MainActor
    func test_localNote_created_pending() async throws {
        let container = try makeContainer()
        let note = LocalNote(date: "2026-01-14", body: "Test note")
        container.mainContext.insert(note)
        try container.mainContext.save()

        let descriptor = FetchDescriptor<LocalNote>()
        let notes = try container.mainContext.fetch(descriptor)
        XCTAssertEqual(notes.count, 1)
        XCTAssertEqual(notes[0].syncState, "pending_create")
        XCTAssertEqual(notes[0].body, "Test note")
    }
}
