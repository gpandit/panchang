package com.pandit.android.ui.theme

import android.graphics.Color as AndroidColor
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.sp

private fun hex(value: String): Color =
    runCatching { Color(AndroidColor.parseColor(value)) }.getOrDefault(Color.Gray)

// TODO(design): single scheme until Aqualeo ships dark tokens.
private fun tokenColorScheme() = lightColorScheme(
    primary = hex(DesignTokens.Color.primary),
    onPrimary = hex(DesignTokens.Color.primaryForeground),
    secondary = hex(DesignTokens.Color.secondary),
    onSecondary = hex(DesignTokens.Color.secondaryForeground),
    background = hex(DesignTokens.Color.background),
    onBackground = hex(DesignTokens.Color.foreground),
    surface = hex(DesignTokens.Color.background),
    onSurface = hex(DesignTokens.Color.foreground),
    error = hex(DesignTokens.Color.destructive),
)

private fun tokenTypography() = Typography(
    bodyLarge = MaterialTheme.typography.bodyLarge.copy(
        fontSize = DesignTokens.Typography.scaleLgSp.sp
    ),
    bodyMedium = MaterialTheme.typography.bodyMedium.copy(
        fontSize = DesignTokens.Typography.scaleBaseSp.sp
    ),
    bodySmall = MaterialTheme.typography.bodySmall.copy(
        fontSize = DesignTokens.Typography.scaleSmSp.sp
    ),
    titleLarge = MaterialTheme.typography.titleLarge.copy(
        fontSize = DesignTokens.Typography.scale2xlSp.sp
    ),
    titleMedium = MaterialTheme.typography.titleMedium.copy(
        fontSize = DesignTokens.Typography.scaleXlSp.sp
    ),
)

val LocalDesignTokens = staticCompositionLocalOf { DesignTokens }

@Composable
fun PanditTheme(content: @Composable () -> Unit) {
    // Reduced-motion check: callers read LocalDesignTokens.Motion.durationBaseMs
    // and should consult Settings.Global.ANIMATOR_DURATION_SCALE (0 = off).
    isSystemInDarkTheme() // retained for future dark-token branching
    MaterialTheme(
        colorScheme = tokenColorScheme(),
        typography = tokenTypography(),
    ) {
        CompositionLocalProvider(LocalDesignTokens provides DesignTokens) {
            content()
        }
    }
}
