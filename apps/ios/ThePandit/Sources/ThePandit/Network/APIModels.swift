// Models mirroring the gateway's OpenAPI contract.
// Do NOT compute anything here — all Panchang data comes from the API.

import Foundation

// MARK: - Envelope

struct APIResponse<T: Decodable>: Decodable {
    let data: T
}

struct PaginatedMeta: Decodable {
    let total: Int
    let page: Int
    let pageSize: Int
    let hasNext: Bool
}

struct PaginatedResponse<T: Decodable>: Decodable {
    let data: [T]
    let meta: PaginatedMeta
}

// MARK: - Panchang

struct TimeValue: Decodable, Hashable {
    let iso: String
    let hour24: String
    let hour12: String
    let hour24Plus: String
}

struct AngaSpan: Decodable, Identifiable, Hashable {
    let index: Int
    let name: String
    let start: TimeValue?
    let end: TimeValue?

    var id: Int { index }
}

struct DayEvents: Decodable {
    let sunrise: TimeValue
    let sunset: TimeValue
    let moonrise: TimeValue?
    let moonset: TimeValue?
}

struct Calendrical: Decodable {
    let shakaSamvat: Int
    let vikramSamvat: Int
    let gujaratiSamvat: Int
    let samvatsara: String
    let ritu: String
    let ayana: String
    let lunarMonth: String
    let isAdhikaMonth: Bool
    let isKshayaMonth: Bool
    let paksha: String
    let moonRashi: String
    let sunRashi: String
}

struct Period: Decodable, Identifiable, Hashable {
    let name: String
    let start: TimeValue
    let end: TimeValue

    var id: String { name + start.iso }
}

struct Choghadiya: Decodable, Identifiable, Hashable {
    let name: String
    let start: TimeValue
    let end: TimeValue
    let isDay: Bool

    var id: String { name + start.iso }
}

struct DailyPanchang: Decodable, Identifiable {
    let date: String
    let lat: Double
    let lon: Double
    let tz: String
    let ayanamsa: String
    let monthScheme: String

    let sunLongitude: Double
    let moonLongitude: Double
    let ayanamsaValue: Double

    let tithi: [AngaSpan]
    let nakshatra: [AngaSpan]
    let yoga: [AngaSpan]
    let karana: [AngaSpan]
    let vara: AngaSpan

    let dayEvents: DayEvents
    let muhurat: [Period]
    let choghadiya: [Choghadiya]
    let hora: [Period]
    let calendrical: Calendrical

    let cached: Bool

    var id: String { "\(date)-\(lat)-\(lon)" }
}

struct MonthCalendar: Decodable {
    let year: Int
    let month: Int
    let days: [DailyPanchang]
}

// MARK: - Festivals

struct Festival: Decodable, Identifiable {
    let id: String
    let name: String
    let date: String
    let description: String?
    let tags: [String]
    let region: String?
    let locale: String?
}

struct FestivalDetail: Decodable, Identifiable {
    let id: String
    let name: String
    let date: String
    let description: String?
    let tags: [String]
    let region: String?
    let locale: String?
    let body: String?
    let puja: String?
    let katha: String?
}

// MARK: - Notes & Reminders

struct Note: Decodable, Identifiable {
    let id: String
    let date: String
    let body: String
    let tags: [String]
    let createdAt: Date
    let updatedAt: Date
}

struct NoteInput: Encodable {
    let date: String
    let body: String
    let tags: [String]
}

struct Reminder: Decodable, Identifiable {
    let id: String
    let title: String
    let triggerType: String
    let triggerValue: String
    let advanceMinutes: Int
    let nextFireAt: Date?
    let isActive: Bool
}

struct ReminderInput: Encodable {
    let title: String
    let triggerType: String
    let triggerValue: String
    let advanceMinutes: Int
}

// MARK: - Profile

struct UserProfile: Decodable {
    let userId: String
    let displayName: String?
    let email: String?
    let preferredAyanamsa: String
    let preferredMonthScheme: String
    let defaultLocation: SavedLocation?
}

struct SavedLocation: Decodable, Identifiable, Encodable {
    let id: String
    let label: String
    let lat: Double
    let lon: Double
    let tz: String
}

// MARK: - Auth

struct TokenResponse: Decodable {
    let accessToken: String
    let refreshToken: String?
    let expiresIn: Int
}
