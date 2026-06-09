// Registers for APNs and forwards the device token to the gateway.
// Handles incoming remote notifications for reminders.

import Foundation
import UserNotifications
import UIKit

@MainActor
final class PushNotificationManager: NSObject, UNUserNotificationCenterDelegate {
    static let shared = PushNotificationManager()

    private let api = APIClient.shared

    func requestAuthorization() async {
        let center = UNUserNotificationCenter.current()
        center.delegate = self
        do {
            let granted = try await center.requestAuthorization(options: [.alert, .badge, .sound])
            if granted {
                await UIApplication.shared.registerForRemoteNotifications()
            }
        } catch {
            // Authorization refused — reminders degrade gracefully to no-op
        }
    }

    func handleDeviceToken(_ tokenData: Data) async {
        let token = tokenData.map { String(format: "%02x", $0) }.joined()
        do {
            try await api.registerPushToken(token)
        } catch {
            // Non-fatal — push still works locally; registration retried on next launch
        }
    }

    func handleRegistrationError(_ error: Error) {
        // APNs registration failed — log the error but don't crash
        // Do NOT log device-identifying info
    }

    // MARK: - UNUserNotificationCenterDelegate

    nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter,
                                            willPresent notification: UNNotification) async
        -> UNNotificationPresentationOptions {
        // Show banner + sound while app is foregrounded
        return [.banner, .sound]
    }

    nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter,
                                            didReceive response: UNNotificationResponse) async {
        // TODO(push): deep-link into the relevant screen based on notification payload
        let userInfo = response.notification.request.content.userInfo
        let _ = userInfo  // payload handling wired in next step
    }
}
