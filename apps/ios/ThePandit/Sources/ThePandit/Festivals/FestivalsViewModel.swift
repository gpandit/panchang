import Foundation
import SwiftData

@MainActor
@Observable
final class FestivalsViewModel {
    var festivals: [Festival] = []
    var selectedFestival: FestivalDetail?
    var isLoading = false
    var isLoadingDetail = false
    var error: String?
    var searchText = ""
    var selectedYear: Int = Calendar.current.component(.year, from: Date())

    private let api = APIClient.shared
    private let cache = OfflineCache.shared

    var filtered: [Festival] {
        guard !searchText.isEmpty else { return festivals }
        return festivals.filter {
            $0.name.localizedCaseInsensitiveContains(searchText) ||
            ($0.description?.localizedCaseInsensitiveContains(searchText) ?? false)
        }
    }

    func load(context: ModelContext) async {
        isLoading = true
        error = nil

        do {
            let page1 = try await api.listFestivals(year: selectedYear)
            festivals = page1.data
            for f in festivals {
                try? await cache.storeFestival(f, context: context)
            }
        } catch {
            let cached = (try? await cache.fetchFestivals(context: context)) ?? []
            if !cached.isEmpty {
                festivals = cached
            } else {
                self.error = (error as? LocalizedError)?.errorDescription ?? "Failed to load festivals."
            }
        }

        isLoading = false
    }

    func loadDetail(id: String) async {
        isLoadingDetail = true
        do {
            selectedFestival = try await api.festivalDetail(id: id)
        } catch {
            self.error = (error as? LocalizedError)?.errorDescription
        }
        isLoadingDetail = false
    }
}
