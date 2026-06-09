import Foundation
import AuthenticationServices

enum AuthState: Equatable {
    case unauthenticated
    case authenticated(userId: String)
    case guest
}

@MainActor
@Observable
final class AuthViewModel: NSObject {
    var authState: AuthState = .unauthenticated
    var isLoading = false
    var errorMessage: String?

    private let tokenManager = AuthTokenManager.shared
    private let api = APIClient.shared

    override init() {
        super.init()
        Task { await restoreSession() }
    }

    // MARK: - Session restoration

    func restoreSession() async {
        let hasToken = await tokenManager.isAuthenticated
        if hasToken {
            // Validate token by fetching profile
            do {
                let profile = try await api.getProfile()
                authState = .authenticated(userId: profile.userId)
            } catch APIError.unauthorized {
                await tokenManager.clear()
                authState = .unauthenticated
            } catch {
                // Network offline — treat existing token as valid
                authState = .authenticated(userId: "cached")
            }
        }
    }

    // MARK: - Apple Sign-In

    func signInWithApple(credential: ASAuthorizationAppleIDCredential) async {
        guard let tokenData = credential.identityToken,
              let token = String(data: tokenData, encoding: .utf8) else {
            errorMessage = "Apple Sign In failed — no identity token."
            return
        }
        await exchangeToken(provider: "apple", idToken: token)
    }

    // MARK: - Google Sign-In

    /// Called with the Google ID token after GIDSignIn completes.
    func signInWithGoogle(idToken: String) async {
        await exchangeToken(provider: "google", idToken: idToken)
    }

    // MARK: - Email Sign-In

    func signInWithEmail(email: String, password: String) async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        struct Body: Encodable { let email: String; let password: String }
        // TODO(auth): wire to gateway /v1/auth/token endpoint when implemented
        errorMessage = "Email sign-in not yet available."
    }

    // MARK: - Guest mode

    func continueAsGuest() {
        authState = .guest
    }

    // MARK: - Sign out

    func signOut() async {
        await tokenManager.clear()
        authState = .unauthenticated
    }

    // MARK: - Private

    private func exchangeToken(provider: String, idToken: String) async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        // TODO(auth): POST to /v1/auth/social with provider + idToken → TokenResponse
        // For now, store the raw idToken as access token (replace with real exchange)
        await tokenManager.store(accessToken: idToken, refreshToken: nil)
        authState = .authenticated(userId: "social")
    }
}
