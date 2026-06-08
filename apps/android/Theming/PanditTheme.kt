// Theme/DesignTokens provider scaffold for Jetpack Compose.
//
// TODO(design): DesignTokens.generated.kt (copy of
// packages/design-tokens/generated/DesignTokens.kt) carries neutral
// placeholder values. Screens reference tokens by name via `MaterialTheme`
// from day one; the design team replaces token *values* and supplies skins —
// this provider and its consumers do not change.
//
// Drop this file (and a synced copy of DesignTokens.generated.kt) into the
// Gradle module when it is scaffolded in Stage 3.

package com.pandit.theming

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.sp
import com.pandit.designtokens.DesignTokens

private fun parseHexColor(value: String): Color =
    runCatching { Color(android.graphics.Color.parseColor(value)) }.getOrDefault(Color.Gray)

private fun colorScheme() = lightColorScheme(
    primary = parseHexColor(DesignTokens.Color.primary),
    onPrimary = parseHexColor(DesignTokens.Color.primaryForeground),
    secondary = parseHexColor(DesignTokens.Color.secondary),
    onSecondary = parseHexColor(DesignTokens.Color.secondaryForeground),
    background = parseHexColor(DesignTokens.Color.background),
    onBackground = parseHexColor(DesignTokens.Color.foreground),
    surface = parseHexColor(DesignTokens.Color.background),
    onSurface = parseHexColor(DesignTokens.Color.foreground),
    error = parseHexColor(DesignTokens.Color.destructive),
)

private fun typography() = Typography(
    bodyLarge = MaterialTheme.typography.bodyLarge.copy(fontSize = 16.sp),
)

/** Tokens exposed to the composition tree — read by name, never hardcoded. */
val LocalDesignTokens = staticCompositionLocalOf { DesignTokens }

/**
 * Wires Compose `MaterialTheme` to the generated token set and provides the
 * cross-cutting accessibility behaviour every screen must honour: reduced
 * motion is read from system animator settings by callers via
 * `LocalDesignTokens` + the platform `Settings.Global.ANIMATOR_DURATION_SCALE`.
 */
@Composable
fun PanditTheme(content: @Composable () -> Unit) {
    // TODO(design): the schema has no dark-mode token variants yet; both
    // branches resolve to the same placeholder scheme today. Once Aqualeo
    // ships dark tokens, branch `colorScheme()` on `isSystemInDarkTheme()`.
    isSystemInDarkTheme()
    MaterialTheme(
        colorScheme = colorScheme(),
        typography = typography(),
    ) {
        androidx.compose.runtime.CompositionLocalProvider(
            LocalDesignTokens provides DesignTokens,
        ) {
            content()
        }
    }
}

/** Parses a token duration string (e.g. "200ms") to milliseconds for Compose `tween`. */
fun motionDurationMillis(tokenValue: String): Int =
    tokenValue.filter { it.isDigit() }.toIntOrNull() ?: 0
