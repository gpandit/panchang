import SwiftUI
import SwiftData

@main
struct ThePanditApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate

    var body: some Scene {
        WindowGroup {
            ThemeProvider {
                AppNavigation()
            }
            .modelContainer(for: [CachedDay.self, CachedFestival.self, LocalNote.self, LocalReminder.self])
        }
    }
}

// MARK: - AppDelegate for APNs registration callbacks

final class AppDelegate: NSObject, UIApplicationDelegate {
    func application(_ application: UIApplication,
                     didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        Task { await PushNotificationManager.shared.handleDeviceToken(deviceToken) }
    }

    func application(_ application: UIApplication,
                     didFailToRegisterForRemoteNotificationsWithError error: Error) {
        PushNotificationManager.shared.handleRegistrationError(error)
    }
}
