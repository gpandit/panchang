# Festival & Vrat Rule Engine

Encodes festivals and vrats as **resolvable rules** (over Tithi / Nakshatra /
Paksha / lunar month / scheme), and resolves them to concrete dates per
location and month-scheme by reading the **cached Panchang** (never
recomputing astronomy here — see `services/panchang`).

Festivals are data, not hard-coded dates (Architecture non-negotiable #4):
`rules.py` declares *what makes a day this festival*; `resolver.py` derives
*which Gregorian date that is*, for a given year/location/scheme, by scanning
cached Panchang days.
