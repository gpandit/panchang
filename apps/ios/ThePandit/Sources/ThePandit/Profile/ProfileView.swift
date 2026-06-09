// TODO(design): all visual styling via DesignTokens.
import SwiftUI

struct ProfileView: View {
    @Bindable var profileVM: ProfileViewModel
    @Bindable var authVM: AuthViewModel

    var body: some View {
        NavigationStack {
            Form {
                if let profile = profileVM.profile {
                    Section("Account") {
                        if let name = profile.displayName {
                            LabeledContent("Name", value: name)
                        }
                        if let email = profile.email {
                            LabeledContent("Email", value: email)
                        }
                    }
                }

                Section("Panchang Preferences") {
                    Picker("Ayanamsa", selection: $profileVM.preferredAyanamsa) {
                        Text("Lahiri (Chitrapaksha)").tag("lahiri")
                        Text("Raman").tag("raman")
                        Text("KP").tag("kp")
                    }
                    .accessibilityLabel("Ayanamsa preference")

                    Picker("Month Scheme", selection: $profileVM.preferredMonthScheme) {
                        Text("Amanta").tag("amanta")
                        Text("Purnimanta").tag("purnimanta")
                    }
                    .accessibilityLabel("Month scheme preference")
                }

                if let loc = profileVM.defaultLocation {
                    Section("Default Location") {
                        LabeledContent("Location", value: loc.label)
                        LabeledContent("Timezone", value: loc.tz)
                    }
                }

                Section {
                    Button(role: .destructive) {
                        Task { await authVM.signOut() }
                    } label: {
                        Text("Sign Out")
                    }
                    .accessibilityLabel("Sign out of your account")
                }
            }
            .navigationTitle("Profile")
            .overlay {
                if profileVM.isLoading {
                    ProgressView()
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .background(.ultraThinMaterial)
                }
            }
        }
        .task { await profileVM.load() }
    }
}
