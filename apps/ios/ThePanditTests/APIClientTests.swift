// Unit tests for the networking client.
// Uses URLProtocol stubbing — never hits a real server.

import XCTest
@testable import ThePandit

final class APIClientTests: XCTestCase {

    // MARK: - Response decoding

    func test_dailyPanchang_decodesSnakeCasePayload() throws {
        // Build a minimal valid DailyPanchang JSON
        let json = """
        {
          "date": "2026-01-14",
          "lat": 28.6139,
          "lon": 77.2090,
          "tz": "Asia/Kolkata",
          "ayanamsa": "lahiri",
          "month_scheme": "amanta",
          "sun_longitude": 293.5,
          "moon_longitude": 120.3,
          "ayanamsa_value": 24.1,
          "tithi": [{"index": 0, "name": "Chaturdashi", "start": null, "end": null}],
          "nakshatra": [{"index": 0, "name": "Uttara Phalguni", "start": null, "end": null}],
          "yoga": [{"index": 0, "name": "Shubha", "start": null, "end": null}],
          "karana": [{"index": 0, "name": "Vishti", "start": null, "end": null}],
          "vara": {"index": 3, "name": "Budhavara", "start": null, "end": null},
          "day_events": {
            "sunrise": {"iso": "2026-01-14T07:15:00+05:30", "hour_24": "07:15", "hour_12": "7:15 AM", "hour_24_plus": "07:15"},
            "sunset":  {"iso": "2026-01-14T17:48:00+05:30", "hour_24": "17:48", "hour_12": "5:48 PM", "hour_24_plus": "17:48"},
            "moonrise": null, "moonset": null
          },
          "muhurat": [],
          "choghadiya": [],
          "hora": [],
          "calendrical": {
            "shaka_samvat": 1948, "vikram_samvat": 2083, "gujarati_samvat": 2082,
            "samvatsara": "Shobhana", "ritu": "Shishira", "ayana": "Uttarayana",
            "lunar_month": "Pausha", "is_adhika_month": false, "is_kshaya_month": false,
            "paksha": "Krishna", "moon_rashi": "Simha", "sun_rashi": "Dhanu"
          },
          "cached": false
        }
        """
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let panchang = try decoder.decode(DailyPanchang.self, from: Data(json.utf8))

        XCTAssertEqual(panchang.date, "2026-01-14")
        XCTAssertEqual(panchang.tithi.first?.name, "Chaturdashi")
        XCTAssertEqual(panchang.vara.name, "Budhavara")
        XCTAssertEqual(panchang.calendrical.lunarMonth, "Pausha")
        XCTAssertFalse(panchang.cached)
    }

    func test_apiResponse_envelope_unwraps() throws {
        let json = """
        {"data": {"id": "f1", "name": "Makar Sankranti", "date": "2026-01-14",
                  "description": null, "tags": ["harvest"], "region": null, "locale": null}}
        """
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let envelope = try decoder.decode(APIResponse<Festival>.self, from: Data(json.utf8))
        XCTAssertEqual(envelope.data.name, "Makar Sankranti")
    }

    func test_paginatedResponse_decodes() throws {
        let json = """
        {"data": [], "meta": {"total": 0, "page": 1, "page_size": 20, "has_next": false}}
        """
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let envelope = try decoder.decode(PaginatedResponse<Festival>.self, from: Data(json.utf8))
        XCTAssertEqual(envelope.meta.total, 0)
        XCTAssertFalse(envelope.meta.hasNext)
    }

    // MARK: - TimeDisplayMode

    func test_timeDisplayMode_allCasesDistinct() {
        let modes = TimeDisplayMode.allCases
        XCTAssertEqual(modes.count, 3)
        XCTAssertEqual(Set(modes.map(\.rawValue)).count, 3)
    }

    // MARK: - CacheKey

    func test_cacheKey_isStable() async {
        let cache = OfflineCache()
        let key1 = await cache.cacheKey(date: "2026-01-14", lat: 28.6, lon: 77.2,
                                         tz: "Asia/Kolkata", ayanamsa: "lahiri", monthScheme: "amanta")
        let key2 = await cache.cacheKey(date: "2026-01-14", lat: 28.6, lon: 77.2,
                                         tz: "Asia/Kolkata", ayanamsa: "lahiri", monthScheme: "amanta")
        XCTAssertEqual(key1, key2)
    }

    func test_cacheKey_differsOnDate() async {
        let cache = OfflineCache()
        let key1 = await cache.cacheKey(date: "2026-01-14", lat: 28.6, lon: 77.2,
                                         tz: "Asia/Kolkata", ayanamsa: "lahiri", monthScheme: "amanta")
        let key2 = await cache.cacheKey(date: "2026-01-15", lat: 28.6, lon: 77.2,
                                         tz: "Asia/Kolkata", ayanamsa: "lahiri", monthScheme: "amanta")
        XCTAssertNotEqual(key1, key2)
    }
}
