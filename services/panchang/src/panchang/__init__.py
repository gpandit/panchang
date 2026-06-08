"""
Panchang Computation Service.

The single source of astronomical truth for The Pandit platform.
All Panchang values are computed here and cached — never recomputed on the client.

Engine parameters (per Architecture Document §5):
  - Ayanamsa:     Lahiri (Chitrapaksha) default; configurable
  - Day boundary: Sunrise-to-sunrise, per location
  - Month scheme: Amanta & Purnimanta, user-selectable
  - Methodology:  Drik Ganita (observational), Swiss Ephemeris

NOTE: pyswisseph integration is wired in Step 0.2.
      The commercial Swiss Ephemeris licence is a hard gate before any public launch.
"""
