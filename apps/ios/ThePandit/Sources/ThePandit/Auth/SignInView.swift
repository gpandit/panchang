import SwiftUI
import AuthenticationServices

// TODO(design): visual styling via DesignTokens — no colours or fonts invented here
struct SignInView: View {
    @Environment(\.designTokens) private var tokens
    @Bindable var viewModel: AuthViewModel

    var body: some View {
        VStack(spacing: 24) {
            // App wordmark placeholder — TODO(design): replace with asset
            Text("The Pandit")
                .font(.largeTitle)
                .accessibilityAddTraits(.isHeader)

            Text("Panchang. Calendar. Guidance.")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            Spacer()

            VStack(spacing: 16) {
                // Apple Sign-In — required for App Store apps that offer social sign-in
                SignInWithAppleButton(
                    onRequest: { request in
                        request.requestedScopes = [.fullName, .email]
                    },
                    onCompletion: { result in
                        switch result {
                        case .success(let auth):
                            guard let credential = auth.credential as? ASAuthorizationAppleIDCredential else { return }
                            Task { await viewModel.signInWithApple(credential: credential) }
                        case .failure(let error):
                            viewModel.errorMessage = error.localizedDescription
                        }
                    }
                )
                .frame(height: 50)
                .accessibilityLabel("Sign in with Apple")

                // Google Sign-In placeholder — integrate GoogleSignIn SDK
                Button {
                    // TODO(auth): launch GIDSignIn flow then call viewModel.signInWithGoogle
                } label: {
                    Label("Sign in with Google", systemImage: "globe")
                        .frame(maxWidth: .infinity)
                        .frame(height: 50)
                }
                .buttonStyle(.bordered)
                .accessibilityLabel("Sign in with Google")

                Divider()

                Button("Continue as Guest") {
                    viewModel.continueAsGuest()
                }
                .font(.footnote)
                .accessibilityHint("Some features require an account")
            }

            if let error = viewModel.errorMessage {
                Text(error)
                    .font(.footnote)
                    .foregroundStyle(.red)
                    .accessibilityLiveRegion(.polite)
            }
        }
        .padding()
        .overlay {
            if viewModel.isLoading {
                ProgressView()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(.ultraThinMaterial)
                    .accessibilityLabel("Signing in…")
            }
        }
    }
}
