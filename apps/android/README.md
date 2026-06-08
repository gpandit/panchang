# apps/android — The Pandit Android App

**Status: placeholder — scaffolded in Stage 3.**

Stack: Native Kotlin · Jetpack Compose · Android Studio

Thin client — reads all Panchang data from `services/api`. No computation on-device.
Birth details stored in an encrypted on-device vault, synced via the Users & Profiles service.

## Theming

`Theming/PanditTheme.kt` is a scaffold wiring Compose `MaterialTheme` to the
generated design tokens — drop it (plus a synced copy of
`packages/design-tokens/generated/DesignTokens.kt`) into the Gradle module
when it's scaffolded in Stage 3. Screens reference tokens by name from day
one; see `packages/design-tokens/INTEGRATING-THE-DESIGN.md`.
