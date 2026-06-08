# libs/ephemeris — Swiss Ephemeris Data Files

## Contents

| File | Description |
|------|-------------|
| `sepl_18.se1` | Planetary ephemeris (Sun, Moon, planets) |
| `semo_18.se1` | Moon (high-precision) |
| `seas_18.se1` | Main-belt asteroids |

## Source

Downloaded from the official Swiss Ephemeris GitHub repository:  
`https://github.com/aloistr/swisseph/tree/master/ephe`

Maintained by Alois Treindl / Astrodienst AG.

## Version

Files downloaded 2026-06-08 from the `master` branch of  
`aloistr/swisseph` (Swiss Ephemeris 2.10.x series).

## Date range covered

These `_18` series files cover **1800 CE – 2400 CE**, which encompasses all
supported Panchang computation dates for The Pandit.

## Licence

The Swiss Ephemeris data files are released under the **GNU Affero General
Public Licence v3 (AGPL)**.

- **Dev / test use** (this repo in its current state) is permitted under AGPL
  because no distributed commercial product is being shipped.
- A **commercial licence from Astrodienst AG** is required before any public
  build (App Store, Play Store, or any sold/monetised distribution) ships.
  See `docs/licensing/swiss-ephemeris.md` for the full policy.

## Usage

The service reads `PANCHANG_EPHEMERIS_PATH` (default: `../../libs/ephemeris`
relative to the service working directory) and passes it to
`swe.set_ephe_path()` at startup. See
`services/panchang/src/panchang/engine.py`.
