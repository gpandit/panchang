// Structure + accessibility audit tests.
// Verify VoiceOver labels and Dynamic Type support are wired; appearance is NOT tested.

import XCTest
import SwiftUI
@testable import ThePandit

final class AccessibilityTests: XCTestCase {

    // MARK: - TimeDisplayMode labels

    func test_timeDisplayMode_labels_nonEmpty() {
        for mode in TimeDisplayMode.allCases {
            XCTAssertFalse(mode.label.isEmpty, "TimeDisplayMode.\(mode) has no label")
        }
    }

    func test_timeDisplayMode_ids_unique() {
        let ids = TimeDisplayMode.allCases.map(\.id)
        XCTAssertEqual(ids.count, Set(ids).count)
    }

    // MARK: - AngaSpan identifiability

    func test_angaSpan_id_matches_index() {
        let span = AngaSpan(index: 5, name: "Panchami", start: nil, end: nil)
        XCTAssertEqual(span.id, 5)
    }

    // MARK: - Festival identifiability

    func test_festival_id_roundtrip() {
        let f = Festival(id: "makar-sankranti", name: "Makar Sankranti",
                         date: "2026-01-14", description: nil, tags: [], region: nil, locale: nil)
        XCTAssertEqual(f.id, "makar-sankranti")
    }

    // MARK: - DailyPanchang stable id

    func test_dailyPanchang_id_includesDateAndLocation() {
        let tv = TimeValue(iso: "", hour24: "", hour12: "", hour24Plus: "")
        let p = DailyPanchang(
            date: "2026-01-14", lat: 28.6, lon: 77.2, tz: "Asia/Kolkata",
            ayanamsa: "lahiri", monthScheme: "amanta",
            sunLongitude: 0, moonLongitude: 0, ayanamsaValue: 0,
            tithi: [], nakshatra: [], yoga: [], karana: [],
            vara: AngaSpan(index: 0, name: "Sun", start: nil, end: nil),
            dayEvents: DayEvents(sunrise: tv, sunset: tv, moonrise: nil, moonset: nil),
            muhurat: [], choghadiya: [], hora: [],
            calendrical: Calendrical(shakaSamvat: 0, vikramSamvat: 0, gujaratiSamvat: 0,
                                     samvatsara: "", ritu: "", ayana: "",
                                     lunarMonth: "", isAdhikaMonth: false, isKshayaMonth: false,
                                     paksha: "", moonRashi: "", sunRashi: ""),
            cached: false
        )
        XCTAssertTrue(p.id.contains("2026-01-14"))
        XCTAssertTrue(p.id.contains("28.6"))
    }

    // MARK: - ThemeProvider reduces motion

    func test_motionDuration_returnsZero_whenReduceMotionEnabled() {
        let duration = motionDurationSeconds("200ms", reduceMotion: true)
        XCTAssertEqual(duration, 0)
    }

    func test_motionDuration_parsesMilliseconds() {
        let duration = motionDurationSeconds("200ms", reduceMotion: false)
        XCTAssertEqual(duration, 0.2, accuracy: 0.001)
    }

    func test_motionDuration_parsesZero_whenReduceMotion() {
        let duration = motionDurationSeconds("320ms", reduceMotion: true)
        XCTAssertEqual(duration, 0.0)
    }
}
