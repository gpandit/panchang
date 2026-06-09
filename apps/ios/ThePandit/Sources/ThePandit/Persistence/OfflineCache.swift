// Read/write helpers for the SwiftData offline cache.
// Cache policy: today + current month + 7 recent days.

import Foundation
import SwiftData

actor OfflineCache {
    static let shared = OfflineCache()

    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    init() {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        d.dateDecodingStrategy = .iso8601
        self.decoder = d
        let e = JSONEncoder()
        e.keyEncodingStrategy = .convertToSnakeCase
        e.dateEncodingStrategy = .iso8601
        self.encoder = e
    }

    // MARK: - Panchang

    func cacheKey(date: String, lat: Double, lon: Double, tz: String,
                  ayanamsa: String, monthScheme: String) -> String {
        "\(date)|\(lat)|\(lon)|\(tz)|\(ayanamsa)|\(monthScheme)"
    }

    func storePanchang(_ panchang: DailyPanchang, context: ModelContext) throws {
        let key = cacheKey(date: panchang.date, lat: panchang.lat, lon: panchang.lon,
                           tz: panchang.tz, ayanamsa: panchang.ayanamsa, monthScheme: panchang.monthScheme)
        let json = try encoder.encode(panchang)

        let descriptor = FetchDescriptor<CachedDay>(predicate: #Predicate { $0.cacheKey == key })
        if let existing = try context.fetch(descriptor).first {
            existing.payloadJSON = json
            existing.cachedAt = Date()
        } else {
            let record = CachedDay(cacheKey: key, date: panchang.date, lat: panchang.lat,
                                   lon: panchang.lon, tz: panchang.tz, ayanamsaKey: panchang.ayanamsa,
                                   monthScheme: panchang.monthScheme, payloadJSON: json)
            context.insert(record)
        }
        try context.save()
    }

    func fetchPanchang(date: String, lat: Double, lon: Double, tz: String,
                       ayanamsa: String, monthScheme: String, context: ModelContext) throws -> DailyPanchang? {
        let key = cacheKey(date: date, lat: lat, lon: lon, tz: tz, ayanamsa: ayanamsa, monthScheme: monthScheme)
        let descriptor = FetchDescriptor<CachedDay>(predicate: #Predicate { $0.cacheKey == key })
        guard let record = try context.fetch(descriptor).first else { return nil }
        return try decoder.decode(DailyPanchang.self, from: record.payloadJSON)
    }

    /// Evicts cached days older than `days` except the current month.
    func evictStale(keepDays days: Int = 7, context: ModelContext) throws {
        let cutoff = Calendar.current.date(byAdding: .day, value: -days, to: Date())!
        let descriptor = FetchDescriptor<CachedDay>(predicate: #Predicate { $0.cachedAt < cutoff })
        let stale = try context.fetch(descriptor)
        for record in stale { context.delete(record) }
        if !stale.isEmpty { try context.save() }
    }

    // MARK: - Festivals

    func storeFestival(_ festival: Festival, context: ModelContext) throws {
        let json = try encoder.encode(festival)
        let id = festival.id
        let descriptor = FetchDescriptor<CachedFestival>(predicate: #Predicate { $0.festivalId == id })
        if let existing = try context.fetch(descriptor).first {
            existing.payloadJSON = json
            existing.cachedAt = Date()
        } else {
            let record = CachedFestival(festivalId: id, payloadJSON: json)
            context.insert(record)
        }
        try context.save()
    }

    func fetchFestivals(context: ModelContext) throws -> [Festival] {
        let descriptor = FetchDescriptor<CachedFestival>()
        let records = try context.fetch(descriptor)
        return try records.compactMap { try decoder.decode(Festival.self, from: $0.payloadJSON) }
    }
}

// Festival needs Encodable too for caching
extension Festival: Encodable {}
extension DailyPanchang: Encodable {}
extension TimeValue: Encodable {}
extension AngaSpan: Encodable {}
extension DayEvents: Encodable {}
extension Calendrical: Encodable {}
extension Period: Encodable {}
extension Choghadiya: Encodable {}
