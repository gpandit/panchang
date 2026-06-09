// Stores and refreshes auth tokens securely in the Keychain.
// Never logs token values.

import Foundation
import Security

actor AuthTokenManager {
    static let shared = AuthTokenManager()

    private let keychainService = "com.pandit.ios"
    private let accessTokenKey = "access_token"
    private let refreshTokenKey = "refresh_token"

    var accessToken: String? {
        get { readKeychain(key: accessTokenKey) }
    }

    func store(accessToken: String, refreshToken: String?) {
        writeKeychain(key: accessTokenKey, value: accessToken)
        if let rt = refreshToken {
            writeKeychain(key: refreshTokenKey, value: rt)
        }
    }

    func clear() {
        deleteKeychain(key: accessTokenKey)
        deleteKeychain(key: refreshTokenKey)
    }

    var isAuthenticated: Bool {
        accessToken != nil
    }

    // MARK: - Keychain helpers

    private func writeKeychain(key: String, value: String) {
        let data = Data(value.utf8)
        let query: [CFString: Any] = [
            kSecClass: kSecClassGenericPassword,
            kSecAttrService: keychainService,
            kSecAttrAccount: key,
        ]
        SecItemDelete(query as CFDictionary)
        var attrs = query
        attrs[kSecValueData] = data
        attrs[kSecAttrAccessible] = kSecAttrAccessibleAfterFirstUnlock
        SecItemAdd(attrs as CFDictionary, nil)
    }

    private func readKeychain(key: String) -> String? {
        let query: [CFString: Any] = [
            kSecClass: kSecClassGenericPassword,
            kSecAttrService: keychainService,
            kSecAttrAccount: key,
            kSecReturnData: true,
            kSecMatchLimit: kSecMatchLimitOne,
        ]
        var result: AnyObject?
        guard SecItemCopyMatching(query as CFDictionary, &result) == errSecSuccess,
              let data = result as? Data,
              let str = String(data: data, encoding: .utf8) else { return nil }
        return str
    }

    private func deleteKeychain(key: String) {
        let query: [CFString: Any] = [
            kSecClass: kSecClassGenericPassword,
            kSecAttrService: keychainService,
            kSecAttrAccount: key,
        ]
        SecItemDelete(query as CFDictionary)
    }
}
