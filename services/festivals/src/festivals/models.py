"""Typed schema for the Festival & Vrat rule engine.

A `FestivalRule` expresses *what makes a day this observance* — a condition
over Tithi / Nakshatra / Paksha / lunar month / scheme, with optional
region-tagged variants. It never names a Gregorian date.

A `FestivalOccurrence` is the *resolved* result: a concrete Gregorian date for
one rule, in one year, at one location, under one month scheme — produced by
`resolver.resolve_year` from the cached Panchang, never invented or stored as
a standalone fact.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, model_validator


class Paksha(StrEnum):
    SHUKLA = "Shukla Paksha"
    KRISHNA = "Krishna Paksha"


class RuleKind(StrEnum):
    """What kind of condition resolves an occurrence."""

    TITHI = "tithi"  # lunar_month + paksha + tithi_index active at sunrise
    NAKSHATRA = "nakshatra"  # lunar_month (+ paksha) + nakshatra active at sunrise
    SANKRANTI = "sankranti"  # the day the Sun enters `sun_rashi` (solar, scheme-independent)
    RECURRING = "recurring"  # cyclic observance — see recurring.RecurringKind


class RegionalVariant(BaseModel):
    """Overrides applied for locations carrying any of `region_tags`.

    Encodes the well-known fact that the *same named festival* can fall on a
    different Tithi/Nakshatra/month in different regions (e.g. Ugadi vs.
    Gudi Padwa share Chaitra Shukla Pratipada, but some festivals genuinely
    shift by tithi or month between traditions). Any field left `None`
    inherits the base rule's value.
    """

    region_tags: list[str]
    name: str | None = None
    lunar_month: str | None = None
    paksha: Paksha | None = None
    tithi_index: int | None = None
    nakshatra_name: str | None = None
    note: str = ""


class FestivalRule(BaseModel):
    """A resolvable rule for a festival or vrat. Data, not a date.

    `lunar_month` is given in **canonical Amanta naming**; the resolver reads
    each candidate day's scheme-correct `Calendrical.lunar_month` (which the
    Panchang engine already adjusts for Amanta/Purnimanta and Adhika maas —
    see `compute._compute_calendrical`) and compares directly, so a festival
    correctly shifts by a month between schemes without the rule changing.
    """

    id: str
    name: str
    kind: RuleKind
    category: str = "festival"  # "festival" | "vrat"

    lunar_month: str | None = None
    paksha: Paksha | None = None
    tithi_index: int | None = None  # 1..15, position within the paksha
    nakshatra_name: str | None = None
    sun_rashi: str | None = None  # for RuleKind.SANKRANTI

    # Whether this rule should resolve in an Adhika (leap) instance of its
    # lunar_month. Most festivals deliberately skip the leap month and wait
    # for the next, regular occurrence of their month; a minority (vrats tied
    # to Adhika Maas itself) want the opposite.
    observe_in_adhika_month: bool = False

    region_tags: list[str] = []
    variants: list[RegionalVariant] = []
    notes: str = ""

    @model_validator(mode="after")
    def _kind_requires_fields(self) -> FestivalRule:
        if self.kind is RuleKind.TITHI and (self.tithi_index is None or self.paksha is None):
            raise ValueError("TITHI rules require `paksha` and `tithi_index`")
        if self.kind is RuleKind.NAKSHATRA and self.nakshatra_name is None:
            raise ValueError("NAKSHATRA rules require `nakshatra_name`")
        if self.kind is RuleKind.SANKRANTI and self.sun_rashi is None:
            raise ValueError("SANKRANTI rules require `sun_rashi`")
        return self

    def for_region(self, region_tags: list[str]) -> FestivalRule:
        """Return a copy of this rule with the first matching variant applied.

        Variants are checked in declaration order; the first whose
        `region_tags` intersects the location's tags wins. No match leaves
        the base rule untouched.
        """
        tags = set(region_tags)
        for variant in self.variants:
            if tags & set(variant.region_tags):
                return self.model_copy(
                    update={
                        k: v
                        for k, v in {
                            "name": variant.name,
                            "lunar_month": variant.lunar_month,
                            "paksha": variant.paksha,
                            "tithi_index": variant.tithi_index,
                            "nakshatra_name": variant.nakshatra_name,
                        }.items()
                        if v is not None
                    }
                )
        return self


class FestivalOccurrence(BaseModel):
    """A resolved, concrete date for one rule at one location/scheme/year."""

    rule_id: str
    name: str
    category: str
    date: date  # Gregorian civil date the Panchang day opens (sunrise)
    lunar_month: str
    paksha: str
    tithi_name: str
    is_adhika_month: bool
    is_kshaya_month: bool
    note: str = ""
