package com.pandit.android.ui.navigation

sealed class NavRoutes(val route: String) {
    object Auth : NavRoutes("auth")
    object Today : NavRoutes("today")
    object Calendar : NavRoutes("calendar")
    object Festivals : NavRoutes("festivals")
    object FestivalDetail : NavRoutes("festivals/{festivalId}") {
        fun with(id: String) = "festivals/$id"
    }
    object Profile : NavRoutes("profile")
}
