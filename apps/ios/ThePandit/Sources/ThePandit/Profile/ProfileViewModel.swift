import Foundation

@MainActor
@Observable
final class ProfileViewModel {
    var profile: UserProfile?
    var isLoading = false
    var error: String?

    // User preferences (locally persisted + synced)
    var preferredAyanamsa: String = "lahiri"
    var preferredMonthScheme: String = "amanta"
    var defaultLocation: SavedLocation?

    private let api = APIClient.shared

    func load() async {
        isLoading = true
        error = nil
        do {
            let p = try await api.getProfile()
            profile = p
            preferredAyanamsa = p.preferredAyanamsa
            preferredMonthScheme = p.preferredMonthScheme
            defaultLocation = p.defaultLocation
        } catch APIError.unauthorized {
            // Guest mode — no profile
        } catch {
            self.error = (error as? LocalizedError)?.errorDescription
        }
        isLoading = false
    }
}
