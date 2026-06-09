import XCTest
import SwiftData
import CoreLocation
@testable import ThePandit

@MainActor
final class TodayViewModelTests: XCTestCase {

    func test_initialState() {
        let vm = TodayViewModel()
        XCTAssertNil(vm.panchang)
        XCTAssertFalse(vm.isLoading)
        XCTAssertNil(vm.error)
        XCTAssertEqual(vm.timeMode, .hour12)
        XCTAssertFalse(vm.isBookmarked)
    }

    func test_timeModeFormatting_hour12() {
        let vm = TodayViewModel()
        vm.timeMode = .hour12
        let tv = TimeValue(iso: "T07:15:00", hour24: "07:15", hour12: "7:15 AM", hour24Plus: "07:15")
        XCTAssertEqual(vm.formatted(tv), "7:15 AM")
    }

    func test_timeModeFormatting_hour24() {
        let vm = TodayViewModel()
        vm.timeMode = .hour24
        let tv = TimeValue(iso: "T17:48:00", hour24: "17:48", hour12: "5:48 PM", hour24Plus: "17:48")
        XCTAssertEqual(vm.formatted(tv), "17:48")
    }

    func test_timeModeFormatting_hour24plus() {
        let vm = TodayViewModel()
        vm.timeMode = .hour24plus
        let tv = TimeValue(iso: "T01:00:00", hour24: "01:00", hour12: "1:00 AM", hour24Plus: "25:00")
        XCTAssertEqual(vm.formatted(tv), "25:00")
    }

    func test_shareText_withoutPanchang_isEmpty() {
        let vm = TodayViewModel()
        XCTAssertTrue(vm.shareText.isEmpty)
    }

    func test_noLoad_withoutLocation() async throws {
        let config = ModelConfiguration(isStoredInMemoryOnly: true)
        let container = try ModelContainer(for: CachedDay.self, CachedFestival.self,
                                           LocalNote.self, LocalReminder.self,
                                           configurations: config)
        let vm = TodayViewModel()
        vm.location = nil  // no location set
        await vm.load(context: container.mainContext)
        // Without a location, loading should be a no-op
        XCTAssertNil(vm.panchang)
        XCTAssertFalse(vm.isLoading)
    }
}
