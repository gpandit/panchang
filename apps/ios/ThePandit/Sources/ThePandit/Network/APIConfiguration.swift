import Foundation

enum APIConfiguration {
    // Override via the PANDIT_API_BASE_URL environment variable or xcconfig
    static var baseURL: URL {
        if let override = ProcessInfo.processInfo.environment["PANDIT_API_BASE_URL"],
           let url = URL(string: override) {
            return url
        }
        // TODO(infra): replace with production gateway URL in release xcconfig
        return URL(string: "https://api.pandit.app")!
    }
}
