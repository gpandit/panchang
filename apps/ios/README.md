# apps/ios — The Pandit iOS App

**Status: placeholder — scaffolded in Stage 3.**

Stack: Native Swift · SwiftUI · Xcode 16+

Thin client — reads all Panchang data from `services/api`. No computation on-device.
Birth details stored in an encrypted on-device vault, synced via the Users & Profiles service.

## Theming

`Theming/ThemeProvider.swift` is a scaffold for the SwiftUI Environment-based
design-token provider — drop it (plus a synced copy of
`packages/design-tokens/generated/DesignTokens.swift`) into the Xcode project
when it's scaffolded in Stage 3. Screens reference tokens by name from day
one; see `packages/design-tokens/INTEGRATING-THE-DESIGN.md`.
