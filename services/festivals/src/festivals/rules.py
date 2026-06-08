"""Curated `FestivalRule` definitions for major pan-Indian festivals.

Each rule encodes the *condition* that defines the festival — never a date.

`lunar_month` values are the engine's own `Calendrical.lunar_month` labels for
the festival's defining Tithi/Paksha day at the reference location (verified
against `tools/accuracy_harness/data/reference_festivals.json`) — not popular
almanac convention, which can disagree with the engine's solar-rashi-anchored
naming by one month for festivals whose lunar month spans a Sankranti (e.g.
this engine names the month containing Gudi Padwa "Phalguna" where many
published Panchangs say "Chaitra"). The architecture makes the engine the
single source of astronomical truth, so the rule must match *its* labels —
matching a second, independently-asserted name would silently mis-resolve
every year this naming nuance recurs. Amanta naming is still what travels
across schemes: the resolver reads each candidate day's scheme-correct
`Calendrical.lunar_month` directly, so the same rule resolves correctly under
both Amanta and Purnimanta (Architecture §5 — "a festival can shift by a month
between conventions").

This is a starting/curated set for harness cross-checking (Step 2.2's "Done
when" criterion); the CMS (Step 2.3) owns growing the catalogue and any
editorial content (katha, puja vidhi).
"""

from __future__ import annotations

from festivals.models import FestivalRule, Paksha, RegionalVariant, RuleKind

DIWALI = FestivalRule(
    id="diwali",
    name="Diwali (Lakshmi Puja)",
    kind=RuleKind.TITHI,
    category="festival",
    lunar_month="Ashwina",
    paksha=Paksha.KRISHNA,
    tithi_index=15,  # Amavasya
    notes="Krishna Paksha Amavasya of Ashwina (Amanta) — Kartika in Purnimanta regions.",
)

HOLI = FestivalRule(
    id="holi",
    name="Holi (Holika Dahan + Rangwali Holi)",
    kind=RuleKind.TITHI,
    category="festival",
    lunar_month="Phalguna",
    paksha=Paksha.SHUKLA,
    tithi_index=15,  # Purnima
    notes="Phalguna Purnima.",
)

RAKSHA_BANDHAN = FestivalRule(
    id="raksha-bandhan",
    name="Raksha Bandhan",
    kind=RuleKind.TITHI,
    category="festival",
    lunar_month="Shravana",
    paksha=Paksha.SHUKLA,
    tithi_index=15,  # Purnima
)

JANMASHTAMI = FestivalRule(
    id="krishna-janmashtami",
    name="Krishna Janmashtami",
    kind=RuleKind.TITHI,
    category="festival",
    lunar_month="Shravana",
    paksha=Paksha.KRISHNA,
    tithi_index=8,
    variants=[
        RegionalVariant(
            region_tags=["smarta"],
            note="Some Smarta traditions observe a day later when the rule's "
            "tithi+nakshatra (Rohini) co-occurrence falls across sunrise.",
        ),
    ],
)

RAM_NAVAMI = FestivalRule(
    id="ram-navami",
    name="Ram Navami",
    kind=RuleKind.TITHI,
    category="festival",
    lunar_month="Chaitra",
    paksha=Paksha.SHUKLA,
    tithi_index=9,
)

GANESH_CHATURTHI = FestivalRule(
    id="ganesh-chaturthi",
    name="Ganesh Chaturthi",
    kind=RuleKind.TITHI,
    category="festival",
    lunar_month="Shravana",
    paksha=Paksha.SHUKLA,
    tithi_index=4,
)

MAHA_SHIVARATRI = FestivalRule(
    id="maha-shivaratri",
    name="Maha Shivaratri",
    kind=RuleKind.TITHI,
    category="festival",
    lunar_month="Magha",
    paksha=Paksha.KRISHNA,
    tithi_index=14,
)

NAVARATRI_START = FestivalRule(
    id="sharad-navaratri-start",
    name="Sharad Navaratri (Ghatasthapana)",
    kind=RuleKind.TITHI,
    category="festival",
    lunar_month="Bhadrapada",
    paksha=Paksha.SHUKLA,
    tithi_index=1,
)

VIJAYADASHAMI = FestivalRule(
    id="vijayadashami",
    name="Vijayadashami (Dussehra)",
    kind=RuleKind.TITHI,
    category="festival",
    lunar_month="Bhadrapada",
    paksha=Paksha.SHUKLA,
    tithi_index=10,
)

GUDI_PADWA = FestivalRule(
    id="gudi-padwa-ugadi",
    name="Gudi Padwa / Ugadi (lunisolar new year)",
    kind=RuleKind.TITHI,
    category="festival",
    lunar_month="Phalguna",
    paksha=Paksha.SHUKLA,
    tithi_index=1,
    region_tags=["maharashtra", "karnataka", "andhra", "telangana"],
    variants=[
        RegionalVariant(region_tags=["maharashtra"], name="Gudi Padwa"),
        RegionalVariant(region_tags=["karnataka", "andhra", "telangana"], name="Ugadi"),
    ],
)

ONAM = FestivalRule(
    id="onam-thiruvonam",
    name="Onam (Thiruvonam)",
    kind=RuleKind.NAKSHATRA,
    category="festival",
    lunar_month="Shravana",
    paksha=Paksha.SHUKLA,
    tithi_index=12,
    nakshatra_name="Shravana",
    region_tags=["kerala"],
    notes="Thiruvonam = Shravana nakshatra falling on Shukla Dwadashi of (Amanta) "
    "Shravana per this engine's naming. The Shravana nakshatra recurs roughly "
    "every 27 days, so it lands more than once within the engine's (longer "
    "than one synodic month, due to its mid-month renaming behaviour around a "
    "Sankranti) 'Shravana'-labelled span — the Tithi pins down the Onam one. "
    "Chingam in the Malayalam solar calendar.",
)

MAKAR_SANKRANTI = FestivalRule(
    id="makar-sankranti",
    name="Makar Sankranti",
    kind=RuleKind.SANKRANTI,
    category="festival",
    sun_rashi="Makara",
    notes="Solar festival — the day the Sun enters Makara rashi; scheme-independent.",
)

MAJOR_FESTIVAL_RULES: list[FestivalRule] = [
    DIWALI,
    HOLI,
    RAKSHA_BANDHAN,
    JANMASHTAMI,
    RAM_NAVAMI,
    GANESH_CHATURTHI,
    MAHA_SHIVARATRI,
    NAVARATRI_START,
    VIJAYADASHAMI,
    GUDI_PADWA,
    ONAM,
    MAKAR_SANKRANTI,
]

RULES_BY_ID: dict[str, FestivalRule] = {rule.id: rule for rule in MAJOR_FESTIVAL_RULES}
