import Foundation
import SwiftData
import CoreLocation

// Time display mode matching the gateway's three forms
enum TimeDisplayMode: String, CaseIterable, Identifiable {
    case hour12 = "12h"
    case hour24 = "24h"
    case hour24plus = "24+"

    var id: String { rawValue }
    var label: String { rawValue }
}

@MainActor
@Observable
final class TodayViewModel {
    var panchang: DailyPanchangViewOut?
    var isLoading = false
    var error: String?
    var timeMode: TimeDisplayMode = .hour12
    var isBookmarked = false
    var showExplanation: PanchangElementViewOut? = nil
    var showMuhuratExplanation: MuhuratWindowViewOut? = nil

    // Location — provided by the app's location manager
    var location: CLLocation?
    var timezone: TimeZone = .current

    private let api = APIClient.shared
    private let cache = OfflineCache.shared

    func load(context: ModelContext) async {
        guard let location else { return }
        isLoading = true
        error = nil

        let dateStr = ISO8601DateFormatter().string(from: Date()).prefix(10).description
        let lat = location.coordinate.latitude
        let lon = location.coordinate.longitude
        let tz = timezone.identifier

        do {
            let result = try await api.dailyPanchang(date: dateStr, lat: lat, lon: lon, tz: tz)
            panchang = result
            try? await cache.storeDailyView(result, ayanamsa: "lahiri", monthScheme: "amanta", context: context)
        } catch {
            // Fall back to cache
            if let cached = try? await cache.fetchDailyView(date: dateStr, lat: lat, lon: lon, tz: tz,
                                                            ayanamsa: "lahiri", monthScheme: "amanta",
                                                            context: context) {
                panchang = cached
            } else {
                self.error = (error as? LocalizedError)?.errorDescription ?? "Failed to load Panchang."
            }
        }

        isLoading = false
    }

    // MARK: - Time formatting

    func formatted(_ value: TimeValue) -> String {
        switch timeMode {
        case .hour12: return value.hour12
        case .hour24: return value.hour24
        case .hour24plus: return value.hour24Plus
        }
    }

    func formatted(_ value: String?) -> String {
        value ?? "—"
    }

    // MARK: - Share

    var shareText: String {
        guard let p = panchang else { return "" }
        let tithi = p.elements.first(where: { $0.key == "tithi" })?.value ?? ""
        let nakshatra = p.elements.first(where: { $0.key == "nakshatra" })?.value ?? ""
        return "Today's Panchang (\(p.date)): Tithi – \(tithi), Nakshatra – \(nakshatra). via The Pandit"
    }
}
