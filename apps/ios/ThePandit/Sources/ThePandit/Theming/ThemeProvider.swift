// Theme/DesignTokens provider scaffold for SwiftUI.
//
// TODO(design): DesignTokens.generated.swift (copy of
// packages/design-tokens/generated/DesignTokens.swift) carries neutral
// placeholder values. Screens reference `Theme.tokens` by name from day one;
// the design team replaces token *values* and supplies skins — this provider
// and its consumers do not change.
//
// Drop this file (and a synced copy of DesignTokens.generated.swift) into the
// Xcode project when it is scaffolded in Stage 3.

import SwiftUI

/// Injected via the SwiftUI Environment so any descendant view can read
/// tokens by name: `@Environment(\.designTokens) var tokens`.
private struct DesignTokensKey: EnvironmentKey {
    static let defaultValue = DesignTokens.self
}

extension EnvironmentValues {
    var designTokens: DesignTokens.Type {
        get { self[DesignTokensKey.self] }
        set { self[DesignTokensKey.self] = newValue }
    }
}

/// Wraps a view subtree with the token environment plus the cross-cutting
/// accessibility behaviour every screen must honour regardless of skin:
/// reduced motion and (eventually) dynamic type / contrast adjustments.
struct ThemeProvider<Content: View>: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    let content: () -> Content

    var body: some View {
        content()
            .environment(\.designTokens, DesignTokens.self)
            .transaction { transaction in
                if reduceMotion {
                    transaction.animation = nil
                }
            }
    }
}

/// Resolves a token duration string (e.g. "200ms") to seconds for
/// SwiftUI's `Animation`, returning zero when Reduce Motion is enabled —
/// use instead of hardcoding animation durations.
func motionDurationSeconds(_ tokenValue: String, reduceMotion: Bool) -> Double {
    guard !reduceMotion else { return 0 }
    let digits = tokenValue.filter { $0.isNumber || $0 == "." }
    guard let milliseconds = Double(digits) else { return 0 }
    return milliseconds / 1000
}
