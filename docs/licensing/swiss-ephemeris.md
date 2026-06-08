# Swiss Ephemeris — Licensing Posture

## Current state: FREE AGPL build (dev / test only)

The Panchang computation service uses
[Swiss Ephemeris](https://www.astro.com/swisseph/) via the
[`pyswisseph`](https://pypi.org/project/pyswisseph/) Python binding.

Swiss Ephemeris is dual-licensed by Astrodienst AG:

| Licence | When it applies |
|---------|-----------------|
| **GNU AGPL v3** | Open-source / non-commercial use |
| **Commercial licence** | Any distribution of a product where end users pay, or any closed-source distribution |

**The Pandit currently uses the free AGPL build.**  
This is permitted during internal development and testing, while no
distributed commercial product is being shipped.

---

## Hard launch gate — commercial licence required

> **The commercial licence MUST be acquired before any of the following:**
>
> - Public App Store (iOS) submission
> - Public Play Store (Android) submission
> - Any sold, monetised, or broadly distributed build
> - Any production server that serves paying or anonymous public users

This is defined as a **hard launch gate** in the Development Plan (Stage 3
hardening, Prompt 3.8).  It is enforced in CI: any build with
`BUILD_PROFILE=production` will fail the `check_launch_readiness` check
until `EPHEMERIS_LICENSE=commercial`.

### How to acquire the commercial licence

Contact Astrodienst AG:  
`https://www.astro.com/swisseph/swephinfo_e.htm#licencing`

Once acquired:
1. Set `EPHEMERIS_LICENSE=commercial` in the production secrets store.
2. Do NOT commit licence keys to this repository.
3. Update the tracked task below and close the gate.

---

## Build / CI gate

| Env var | Allowed values | Default |
|---------|---------------|---------|
| `PANCHANG_EPHEMERIS_LICENSE` | `agpl`, `commercial` | `agpl` |
| `PANCHANG_BUILD_PROFILE` | `development`, `staging`, `production` | `development` |

The script `tools/check_launch_readiness.py` exits non-zero when
`BUILD_PROFILE=production` and `EPHEMERIS_LICENSE=agpl`.

The CI job `.github/workflows/launch-readiness.yml` runs this check on
every push to `main` and on any build tagged `production`.

---

## Tracked task

**LAUNCH-GATE-001**: Acquire Astrodienst commercial licence before first
public release.  
Owner: TBD — assign to the person responsible for legal / vendor contracts.  
Mirrored in: Development Plan Prompt 3.8 ("Stage 3 hardening").

---

## References

- Swiss Ephemeris licence page: <https://www.astro.com/swisseph/swephinfo_e.htm#licencing>
- AGPL v3 full text: <https://www.gnu.org/licenses/agpl-3.0.html>
- Ephemeris data files: `libs/ephemeris/README.md`
- Launch-readiness check: `tools/check_launch_readiness.py`
