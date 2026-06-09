"""Resolver unit tests against a synthetic, controllable Panchang source.

These exercise the rule->occurrence logic in isolation (Vriddhi-tithi
collapsing, Adhika-month preference, Sankranti transition detection, scheme
shift) without paying for a full year of Swiss-Ephemeris computes — that
cross-check against the real engine lives in test_harness_crosscheck.py.
"""

from __future__ import annotations

from datetime import date

from festivals.models import FestivalRule, Paksha, RegionalVariant, RuleKind
from festivals.recurring import RecurringKind, generate_year
from festivals.resolver import resolve_year

from .factories import fake_result

YEAR = 2024


def _const_source(spec: dict[date, dict]):
    """A PanchangSource backed by a per-date dict of `fake_result` kwargs.
    Dates absent from `spec` repeat the most recent preceding entry — lets a
    test describe only the days that change."""
    days = sorted(spec)

    def source(d: date):
        chosen = days[0]
        for cand in days:
            if cand <= d:
                chosen = cand
            else:
                break
        return fake_result(d, **spec[chosen])

    return source


# ──────────────────────────────────────────────────────────────────────────
# Tithi-rule resolution
# ──────────────────────────────────────────────────────────────────────────


def test_resolves_single_tithi_match() -> None:
    rule = FestivalRule(
        id="test-diwali",
        name="Test Diwali",
        kind=RuleKind.TITHI,
        lunar_month="Ashwina",
        paksha=Paksha.KRISHNA,
        tithi_index=15,
    )
    source = _const_source(
        {
            date(YEAR, 1, 1): {
                "tithi_index": 1,
                "lunar_month": "Chaitra",
                "paksha": "Shukla Paksha",
            },
            date(YEAR, 11, 1): {
                "tithi_index": 30,
                "lunar_month": "Ashwina",
                "paksha": "Krishna Paksha",
            },
            date(YEAR, 11, 2): {
                "tithi_index": 1,
                "lunar_month": "Kartika",
                "paksha": "Shukla Paksha",
            },
        }
    )

    occurrences = resolve_year(rule, YEAR, source)

    assert len(occurrences) == 1
    assert occurrences[0].date == date(YEAR, 11, 1)
    assert occurrences[0].lunar_month == "Ashwina"
    assert occurrences[0].tithi_name == "Amavasya"


def test_vriddhi_tithi_collapses_to_first_sunrise() -> None:
    """When a Tithi is active at two consecutive sunrises (Vriddhi), the
    festival is observed on the first (udaya-vyApti) day, not both."""
    rule = FestivalRule(
        id="test-ramnavami",
        name="Test Ram Navami",
        kind=RuleKind.TITHI,
        lunar_month="Chaitra",
        paksha=Paksha.SHUKLA,
        tithi_index=9,
    )
    # Two consecutive sunrises (16th, 17th) report the same global tithi
    # index 9 — a Vriddhi — and the festival should land on the first.
    spec_days = {
        date(YEAR, 1, 1): {"tithi_index": 8, "lunar_month": "Chaitra", "paksha": "Shukla Paksha"},
        date(YEAR, 4, 16): {"tithi_index": 9, "lunar_month": "Chaitra", "paksha": "Shukla Paksha"},
        date(YEAR, 4, 17): {"tithi_index": 9, "lunar_month": "Chaitra", "paksha": "Shukla Paksha"},
        date(YEAR, 4, 18): {"tithi_index": 10, "lunar_month": "Chaitra", "paksha": "Shukla Paksha"},
    }
    source = _const_source(spec_days)

    occurrences = resolve_year(rule, YEAR, source)

    assert len(occurrences) == 1
    assert occurrences[0].date == date(YEAR, 4, 16)


def test_prefers_non_adhika_occurrence_of_named_month() -> None:
    """A festival's lunar month can occur twice (an Adhika instance plus the
    regular one). Unless the rule opts in, the regular occurrence wins."""
    rule = FestivalRule(
        id="test-rakhi",
        name="Test Raksha Bandhan",
        kind=RuleKind.TITHI,
        lunar_month="Shravana",
        paksha=Paksha.SHUKLA,
        tithi_index=15,
    )
    spec = {
        date(YEAR, 1, 1): {"tithi_index": 1, "lunar_month": "Chaitra", "paksha": "Shukla Paksha"},
        date(YEAR, 7, 20): {
            "tithi_index": 15,
            "lunar_month": "Shravana",
            "paksha": "Shukla Paksha",
            "is_adhika_month": True,
        },
        date(YEAR, 7, 21): {
            "tithi_index": 1,
            "lunar_month": "Shravana",
            "paksha": "Krishna Paksha",
        },
        date(YEAR, 8, 19): {
            "tithi_index": 15,
            "lunar_month": "Shravana",
            "paksha": "Shukla Paksha",
            "is_adhika_month": False,
        },
        date(YEAR, 8, 20): {
            "tithi_index": 1,
            "lunar_month": "Bhadrapada",
            "paksha": "Krishna Paksha",
        },
    }
    source = _const_source(spec)

    occurrences = resolve_year(rule, YEAR, source)

    assert len(occurrences) == 1
    assert occurrences[0].date == date(YEAR, 8, 19)
    assert occurrences[0].is_adhika_month is False


def test_falls_back_to_adhika_occurrence_when_no_regular_one_exists() -> None:
    rule = FestivalRule(
        id="test-only-adhika",
        name="Test Only-Adhika",
        kind=RuleKind.TITHI,
        lunar_month="Shravana",
        paksha=Paksha.SHUKLA,
        tithi_index=15,
    )
    spec = {
        date(YEAR, 1, 1): {"tithi_index": 1, "lunar_month": "Chaitra", "paksha": "Shukla Paksha"},
        date(YEAR, 7, 20): {
            "tithi_index": 15,
            "lunar_month": "Shravana",
            "paksha": "Shukla Paksha",
            "is_adhika_month": True,
        },
        date(YEAR, 7, 21): {
            "tithi_index": 1,
            "lunar_month": "Bhadrapada",
            "paksha": "Krishna Paksha",
        },
    }
    source = _const_source(spec)

    occurrences = resolve_year(rule, YEAR, source)

    assert len(occurrences) == 1
    assert occurrences[0].date == date(YEAR, 7, 20)
    assert occurrences[0].is_adhika_month is True


def test_no_match_returns_empty() -> None:
    rule = FestivalRule(
        id="test-nomatch",
        name="Test No Match",
        kind=RuleKind.TITHI,
        lunar_month="Pausha",
        paksha=Paksha.SHUKLA,
        tithi_index=5,
    )
    source = _const_source(
        {date(YEAR, 1, 1): {"tithi_index": 1, "lunar_month": "Chaitra", "paksha": "Shukla Paksha"}}
    )

    assert resolve_year(rule, YEAR, source) == []


# ──────────────────────────────────────────────────────────────────────────
# Nakshatra-rule resolution
# ──────────────────────────────────────────────────────────────────────────


def test_resolves_nakshatra_rule() -> None:
    rule = FestivalRule(
        id="test-onam",
        name="Test Onam",
        kind=RuleKind.NAKSHATRA,
        lunar_month="Bhadrapada",
        nakshatra_name="Shravana",
    )
    spec = {
        date(YEAR, 1, 1): {
            "tithi_index": 1,
            "lunar_month": "Chaitra",
            "paksha": "Shukla Paksha",
            "nakshatra_name": "Ashwini",
        },
        date(YEAR, 9, 15): {
            "tithi_index": 10,
            "lunar_month": "Bhadrapada",
            "paksha": "Shukla Paksha",
            "nakshatra_name": "Shravana",
        },
        date(YEAR, 9, 16): {
            "tithi_index": 11,
            "lunar_month": "Bhadrapada",
            "paksha": "Shukla Paksha",
            "nakshatra_name": "Dhanishta",
        },
    }
    source = _const_source(spec)

    occurrences = resolve_year(rule, YEAR, source)

    assert len(occurrences) == 1
    assert occurrences[0].date == date(YEAR, 9, 15)


# ──────────────────────────────────────────────────────────────────────────
# Sankranti resolution
# ──────────────────────────────────────────────────────────────────────────


def test_resolves_sankranti_transition_day() -> None:
    rule = FestivalRule(
        id="test-makar", name="Test Makar Sankranti", kind=RuleKind.SANKRANTI, sun_rashi="Makara"
    )
    spec = {
        date(YEAR, 1, 1): {
            "tithi_index": 1,
            "lunar_month": "Pausha",
            "paksha": "Shukla Paksha",
            "sun_rashi": "Dhanu",
        },
        date(YEAR, 1, 15): {
            "tithi_index": 15,
            "lunar_month": "Pausha",
            "paksha": "Shukla Paksha",
            "sun_rashi": "Makara",
        },
    }
    source = _const_source(spec)

    occurrences = resolve_year(rule, YEAR, source)

    assert len(occurrences) == 1
    assert occurrences[0].date == date(YEAR, 1, 15)
    assert occurrences[0].name == "Test Makar Sankranti"


# ──────────────────────────────────────────────────────────────────────────
# Region variants & scheme shift
# ──────────────────────────────────────────────────────────────────────────


def test_regional_variant_overrides_name_and_criteria() -> None:
    rule = FestivalRule(
        id="test-newyear",
        name="Generic New Year",
        kind=RuleKind.TITHI,
        lunar_month="Chaitra",
        paksha=Paksha.SHUKLA,
        tithi_index=1,
        region_tags=["maharashtra", "karnataka"],
        variants=[RegionalVariant(region_tags=["karnataka"], name="Ugadi")],
    )
    spec = {
        date(YEAR, 4, 9): {"tithi_index": 1, "lunar_month": "Chaitra", "paksha": "Shukla Paksha"}
    }
    source = _const_source(spec)

    by_region = resolve_year(rule, YEAR, source, region_tags=["karnataka"])
    assert by_region[0].name == "Ugadi"

    by_other_region = resolve_year(rule, YEAR, source, region_tags=["maharashtra"])
    assert by_other_region[0].name == "Generic New Year"


# ──────────────────────────────────────────────────────────────────────────
# Recurring observances
# ──────────────────────────────────────────────────────────────────────────


def test_recurring_ekadashi_cadence_and_vriddhi_collapse() -> None:
    spec = {
        date(YEAR, 1, 1): {"tithi_index": 1, "lunar_month": "Pausha", "paksha": "Shukla Paksha"},
        date(YEAR, 1, 7): {"tithi_index": 11, "lunar_month": "Pausha", "paksha": "Shukla Paksha"},
        date(YEAR, 1, 8): {"tithi_index": 12, "lunar_month": "Pausha", "paksha": "Shukla Paksha"},
        date(YEAR, 1, 21): {
            "tithi_index": 26,
            "lunar_month": "Pausha",
            "paksha": "Krishna Paksha",
        },  # Krishna Ekadashi (local 11)
        date(YEAR, 1, 22): {
            "tithi_index": 26,
            "lunar_month": "Pausha",
            "paksha": "Krishna Paksha",
        },  # Vriddhi continuation
        date(YEAR, 1, 23): {"tithi_index": 27, "lunar_month": "Pausha", "paksha": "Krishna Paksha"},
    }
    source = _const_source(spec)

    occurrences = generate_year(RecurringKind.EKADASHI, YEAR, source)
    occ_dates = [o.date for o in occurrences]

    assert date(YEAR, 1, 7) in occ_dates
    assert date(YEAR, 1, 21) in occ_dates
    assert date(YEAR, 1, 22) not in occ_dates  # collapsed Vriddhi continuation
    assert all(o.category == "vrat" for o in occurrences)


def test_recurring_purnima_and_amavasya_use_headline_tithi_name() -> None:
    spec = {
        date(YEAR, 1, 1): {"tithi_index": 1, "lunar_month": "Pausha", "paksha": "Shukla Paksha"},
        date(YEAR, 1, 15): {"tithi_index": 15, "lunar_month": "Pausha", "paksha": "Shukla Paksha"},
        date(YEAR, 1, 16): {"tithi_index": 16, "lunar_month": "Pausha", "paksha": "Krishna Paksha"},
        date(YEAR, 1, 30): {"tithi_index": 30, "lunar_month": "Pausha", "paksha": "Krishna Paksha"},
        date(YEAR, 1, 31): {"tithi_index": 1, "lunar_month": "Magha", "paksha": "Shukla Paksha"},
    }
    source = _const_source(spec)

    purnimas = generate_year(RecurringKind.PURNIMA, YEAR, source)
    amavasyas = generate_year(RecurringKind.AMAVASYA, YEAR, source)

    assert any(o.date == date(YEAR, 1, 15) and o.tithi_name == "Purnima" for o in purnimas)
    assert any(o.date == date(YEAR, 1, 30) and o.tithi_name == "Amavasya" for o in amavasyas)


def test_recurring_sankashti_only_fires_on_krishna_chaturthi() -> None:
    spec = {
        date(YEAR, 1, 1): {
            "tithi_index": 4,
            "lunar_month": "Pausha",
            "paksha": "Shukla Paksha",
        },  # Shukla Chaturthi: not Sankashti
        date(YEAR, 1, 19): {
            "tithi_index": 19,
            "lunar_month": "Pausha",
            "paksha": "Krishna Paksha",
        },  # Krishna Chaturthi (local 4)
        date(YEAR, 1, 20): {"tithi_index": 20, "lunar_month": "Pausha", "paksha": "Krishna Paksha"},
    }
    source = _const_source(spec)

    occurrences = generate_year(RecurringKind.SANKASHTI, YEAR, source)

    assert [o.date for o in occurrences] == [date(YEAR, 1, 19)]


def test_recurring_sankranti_generates_one_per_transition() -> None:
    spec = {
        date(YEAR, 1, 1): {
            "tithi_index": 1,
            "lunar_month": "Pausha",
            "paksha": "Shukla Paksha",
            "sun_rashi": "Dhanu",
        },
        date(YEAR, 1, 15): {
            "tithi_index": 15,
            "lunar_month": "Pausha",
            "paksha": "Shukla Paksha",
            "sun_rashi": "Makara",
        },
        date(YEAR, 2, 13): {
            "tithi_index": 4,
            "lunar_month": "Magha",
            "paksha": "Shukla Paksha",
            "sun_rashi": "Kumbha",
        },
    }
    source = _const_source(spec)

    occurrences = generate_year(RecurringKind.SANKRANTI, YEAR, source)
    occ = {(o.date, o.name) for o in occurrences}

    assert (date(YEAR, 1, 15), "Makara Sankranti") in occ
    assert (date(YEAR, 2, 13), "Kumbha Sankranti") in occ
