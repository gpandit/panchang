package com.pandit.android.ui.navigation

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.CalendarMonth
import androidx.compose.material.icons.outlined.Celebration
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material.icons.outlined.WbSunny
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.pandit.android.R
import com.pandit.android.data.repository.AuthState
import com.pandit.android.ui.auth.AuthScreen
import com.pandit.android.ui.auth.AuthViewModel
import com.pandit.android.ui.calendar.CalendarScreen
import com.pandit.android.ui.festivals.FestivalDetailScreen
import com.pandit.android.ui.festivals.FestivalsScreen
import com.pandit.android.ui.profile.ProfileScreen
import com.pandit.android.ui.today.TodayScreen

private data class BottomNavItem(
    val route: String,
    val labelRes: Int,
    val icon: androidx.compose.ui.graphics.vector.ImageVector,
    val contentDescRes: Int,
)

private val bottomNavItems = listOf(
    BottomNavItem(NavRoutes.Today.route, R.string.nav_today, Icons.Outlined.WbSunny, R.string.nav_today),
    BottomNavItem(NavRoutes.Calendar.route, R.string.nav_calendar, Icons.Outlined.CalendarMonth, R.string.nav_calendar),
    BottomNavItem(NavRoutes.Festivals.route, R.string.nav_festivals, Icons.Outlined.Celebration, R.string.nav_festivals),
    BottomNavItem(NavRoutes.Profile.route, R.string.nav_profile, Icons.Outlined.Person, R.string.nav_profile),
)

@Composable
fun PanditNavHost() {
    val authViewModel: AuthViewModel = hiltViewModel()
    val authState by authViewModel.authState.collectAsState()
    val navController = rememberNavController()

    LaunchedEffect(authState) {
        when (authState) {
            is AuthState.SignedOut -> navController.navigate(NavRoutes.Auth.route) {
                popUpTo(0) { inclusive = true }
            }
            is AuthState.Authenticated, is AuthState.Guest -> {
                val current = navController.currentDestination?.route
                if (current == NavRoutes.Auth.route || current == null) {
                    navController.navigate(NavRoutes.Today.route) {
                        popUpTo(0) { inclusive = true }
                    }
                }
            }
            else -> Unit
        }
    }

    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentDestination = navBackStackEntry?.destination
    val showBottomBar = bottomNavItems.any { it.route == currentDestination?.route }

    Scaffold(
        bottomBar = {
            if (showBottomBar) {
                NavigationBar {
                    bottomNavItems.forEach { item ->
                        NavigationBarItem(
                            selected = currentDestination?.hierarchy?.any { it.route == item.route } == true,
                            onClick = {
                                navController.navigate(item.route) {
                                    popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            icon = {
                                Icon(
                                    imageVector = item.icon,
                                    contentDescription = stringResource(item.contentDescRes),
                                )
                            },
                            label = { Text(stringResource(item.labelRes)) },
                        )
                    }
                }
            }
        }
    ) { paddingValues ->
        NavHost(
            navController = navController,
            startDestination = NavRoutes.Auth.route,
            modifier = Modifier.padding(paddingValues),
        ) {
            composable(NavRoutes.Auth.route) {
                AuthScreen(onAuthSuccess = {
                    navController.navigate(NavRoutes.Today.route) {
                        popUpTo(NavRoutes.Auth.route) { inclusive = true }
                    }
                })
            }
            composable(NavRoutes.Today.route) { TodayScreen() }
            composable(NavRoutes.Calendar.route) { CalendarScreen() }
            composable(NavRoutes.Festivals.route) {
                FestivalsScreen(onFestivalClick = { id ->
                    navController.navigate(NavRoutes.FestivalDetail.with(id))
                })
            }
            composable(NavRoutes.FestivalDetail.route) { backStack ->
                val id = backStack.arguments?.getString("festivalId") ?: return@composable
                FestivalDetailScreen(festivalId = id, onBack = { navController.popBackStack() })
            }
            composable(NavRoutes.Profile.route) { ProfileScreen() }
        }
    }
}
