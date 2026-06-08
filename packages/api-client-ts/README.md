# @pandit/api-client-ts

Shared TypeScript API types and client for The Pandit platform.
Used by `apps/web`, `apps/admin`, and the mobile bridge layer.

## Status

Currently contains hand-authored type stubs matching the Architecture Document §7.
In Step 2+ these will be generated from the `services/api` OpenAPI spec.

## Usage

```typescript
import type { PanchangDay, Location } from "@pandit/api-client-ts";
```

## Development

```bash
pnpm run typecheck   # tsc --noEmit
pnpm run test        # vitest run
pnpm run build       # compile to dist/
```
