# The Pandit — iOS App

Native Swift + SwiftUI, iOS 17+. Thin client — reads all Panchang from `services/api`.
No computation on-device.

## Setup

### Prerequisites
- Xcode 16+
- [XcodeGen](https://github.com/yonaskolb/XcodeGen): `brew install xcodegen`

### Generate the Xcode project

```bash
cd apps/ios
xcodegen generate
open ThePandit.xcodeproj
```

### API base URL
Set `PANDIT_API_BASE_URL` in your scheme's environment variables, or create an
`xcconfig` and point the build settings at it. Defaults to `https://api.pandit.app`.

### Design tokens
`ThePandit/Sources/ThePandit/Theming/DesignTokens.generated.swift` is auto-generated from
`packages/design-tokens/src/schema.ts`. All values are `TODO(design)` placeholders.

To regenerate after a token schema change: `pnpm --filter design-tokens build`

## Architecture

| Layer | Files |
|---|---|
| Networking | `Network/APIClient.swift` — actor-isolated HTTP client |
| Auth | `Auth/AuthTokenManager.swift` (Keychain); `Auth/AuthViewModel.swift` |
| Offline | `Persistence/CacheStore.swift` (SwiftData models); `OfflineCache.swift` |
| Screens | `Today/`, `Calendar/`, `Festivals/`, `Profile/` — ViewModel + View each |
| Push | `Push/PushNotificationManager.swift` — APNs registration + token relay |
| Location | `Shared/LocationManager.swift` |
| Theming | `Theming/DesignTokens.generated.swift` + `ThemeProvider.swift` |

## Design constraints

All visual values (colours, fonts, spacing, radius) flow through `DesignTokens`.
Views mark aesthetic gaps with `// TODO(design):`. **Do not invent values.**

## Tests

```bash
xcodebuild test -scheme ThePandit -destination 'platform=iOS Simulator,name=iPhone 16'
```

Covers: API decoding · offline cache round-trip · ViewModel state · Reduce Motion hook · stable Identifiable IDs.

## Offline behaviour

Cache stores today's payload + current month + 7 recent days. Eviction runs via
`OfflineCache.evictStale`. Screens fall back to cached data silently when offline.

## Push notifications (APNs)

`PushNotificationManager` requests authorisation on first launch, registers with APNs,
and forwards the device token to `POST /v1/profile/push-token`. The gateway fan-out
service drives delivery; the app only registers and handles incoming payloads.
