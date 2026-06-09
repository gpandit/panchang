// Root navigation. Screens are composed here; view models are injected.
import SwiftUI
import SwiftData

struct AppNavigation: View {
    @Environment(\.modelContext) private var context
    @State private var authVM = AuthViewModel()
    @State private var locationManager = LocationManager()
    @State private var todayVM = TodayViewModel()
    @State private var calendarVM = CalendarViewModel()
    @State private var festivalsVM = FestivalsViewModel()
    @State private var profileVM = ProfileViewModel()

    var body: some View {
        Group {
            switch authVM.authState {
            case .unauthenticated:
                SignInView(viewModel: authVM)
            case .authenticated, .guest:
                mainTabs
            }
        }
        .onChange(of: locationManager.location) { _, loc in
            todayVM.location = loc
            todayVM.timezone = locationManager.timezone
            calendarVM.location = loc
            calendarVM.timezone = locationManager.timezone
        }
        .task {
            locationManager.requestWhenInUse()
        }
    }

    private var mainTabs: some View {
        TabView {
            TodayView(viewModel: todayVM)
                .tabItem { Label("Today", systemImage: "sun.max") }
                .accessibilityLabel("Today's Panchang")

            CalendarView(viewModel: calendarVM)
                .tabItem { Label("Calendar", systemImage: "calendar") }
                .accessibilityLabel("Panchang calendar")

            FestivalsListView(viewModel: festivalsVM)
                .tabItem { Label("Festivals", systemImage: "sparkles") }
                .accessibilityLabel("Festivals and vrats")

            ProfileView(profileVM: profileVM, authVM: authVM)
                .tabItem { Label("Profile", systemImage: "person.circle") }
                .accessibilityLabel("Profile and settings")
        }
    }
}
