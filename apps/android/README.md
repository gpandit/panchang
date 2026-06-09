# apps/android — The Pandit Android App

**Stack:** Native Kotlin · Jetpack Compose · MVVM + Repositories · Room · Retrofit + Moshi · Hilt · FCM

Thin client — reads all Panchang data from `services/api`. No computation on-device.

---

## Structure

```
app/src/main/java/com/pandit/android/
  MainActivity.kt / PanditApplication.kt
  data/
    api/           ApiService.kt, ApiModels.kt, AuthInterceptor.kt
    db/            PanditDatabase.kt, dao/, entity/
    repository/    PanchangRepository, FestivalRepository, NoteRepository, AuthRepository
  di/              AppModule.kt (Hilt)
  push/            PanditFcmService.kt
  ui/
    theme/         DesignTokens.kt, PanditTheme.kt
    navigation/    PanditNavHost.kt, NavRoutes.kt
    today/         TodayScreen.kt, TodayViewModel.kt
    calendar/      CalendarScreen.kt, CalendarViewModel.kt
    festivals/     FestivalsScreen.kt, FestivalDetailScreen.kt, FestivalsViewModel.kt
    auth/          AuthScreen.kt, AuthViewModel.kt
    profile/       ProfileScreen.kt, ProfileViewModel.kt
  util/            TokenStore.kt, LocationHelper.kt, PrefsStore.kt
```

## Theming

All visual values flow through `ui/theme/DesignTokens.kt` → `PanditTheme.kt` → Compose
`MaterialTheme`. Every `TODO(design)` annotation marks a placeholder to be replaced by the
Aqualeo design system — no colours, fonts, or spacing were invented here.

## Prerequisites

1. **Firebase**: replace `app/google-services.json` with the real file from Firebase Console.
2. **API URL**: override `API_BASE_URL` in `local.properties` for non-emulator targets.
3. **Google Sign-In**: wire the `GoogleSignInClient` launch in `AuthScreen` (marked `TODO`).

## Running

```bash
# From apps/android/
./gradlew :app:assembleDebug
./gradlew :app:connectedAndroidTest   # instrumented tests (requires emulator)
./gradlew :app:test                   # unit tests
```

## Offline behaviour

- Room cache stores today's payload, the current month, and all loaded day entries.
- `observeToday` / `observeMonth` / `observeDay` flows expose cached data immediately;
  a fresh network fetch runs in parallel and updates the cache.
- Offline banner renders when the last fetch failed.
- Cache is evicted after 60 days via `PanchangRepository.evictOldCache`.

## Push notifications

`PanditFcmService` handles `onNewToken` (registers with backend) and `onMessageReceived`
(posts a local notification). Channels: `pandit_reminders` and `pandit_daily`.
