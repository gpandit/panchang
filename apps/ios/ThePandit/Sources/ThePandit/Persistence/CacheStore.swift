// SwiftData models for offline cache.
// Stores today's payload + current month + recent days.
// No Panchang math here — data always originates from the API.

import Foundation
import SwiftData

// MARK: - Cached Panchang Day

@Model
final class CachedDay {
    @Attribute(.unique) var cacheKey: String  // "date|lat|lon|tz|ayanamsa|scheme"
    var date: String
    var lat: Double
    var lon: Double
    var tz: String
    var ayanamsaKey: String
    var monthScheme: String
    var payloadJSON: Data          // raw JSON blob from the API
    var cachedAt: Date

    init(cacheKey: String, date: String, lat: Double, lon: Double, tz: String,
         ayanamsaKey: String, monthScheme: String, payloadJSON: Data) {
        self.cacheKey = cacheKey
        self.date = date
        self.lat = lat
        self.lon = lon
        self.tz = tz
        self.ayanamsaKey = ayanamsaKey
        self.monthScheme = monthScheme
        self.payloadJSON = payloadJSON
        self.cachedAt = Date()
    }
}

// MARK: - Cached Festival

@Model
final class CachedFestival {
    @Attribute(.unique) var festivalId: String
    var payloadJSON: Data
    var cachedAt: Date

    init(festivalId: String, payloadJSON: Data) {
        self.festivalId = festivalId
        self.payloadJSON = payloadJSON
        self.cachedAt = Date()
    }
}

// MARK: - Local Note (user-created, sync-pending)

@Model
final class LocalNote {
    @Attribute(.unique) var localId: String
    var serverId: String?          // nil until synced
    var date: String
    var body: String
    var tags: [String]
    var syncState: String          // "synced" | "pending_create" | "pending_update" | "pending_delete"
    var createdAt: Date
    var updatedAt: Date

    init(localId: String = UUID().uuidString, date: String, body: String, tags: [String] = []) {
        self.localId = localId
        self.date = date
        self.body = body
        self.tags = tags
        self.syncState = "pending_create"
        self.createdAt = Date()
        self.updatedAt = Date()
    }
}

// MARK: - Local Reminder

@Model
final class LocalReminder {
    @Attribute(.unique) var localId: String
    var serverId: String?
    var title: String
    var triggerType: String
    var triggerValue: String
    var advanceMinutes: Int
    var isActive: Bool
    var syncState: String

    init(localId: String = UUID().uuidString, title: String,
         triggerType: String, triggerValue: String, advanceMinutes: Int = 0) {
        self.localId = localId
        self.title = title
        self.triggerType = triggerType
        self.triggerValue = triggerValue
        self.advanceMinutes = advanceMinutes
        self.isActive = true
        self.syncState = "pending_create"
    }
}
