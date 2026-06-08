"""Festival & Vrat Rule Engine — resolves declarative `FestivalRule`s into
dated `FestivalOccurrence`s per location/scheme, reading the cached Panchang.
Festivals are rules, never hard-coded dates (Architecture non-negotiable #4).
"""

from festivals.models import FestivalOccurrence, FestivalRule, Paksha, RegionalVariant, RuleKind
from festivals.resolver import PanchangSource, make_panchang_source, resolve_year

__all__ = [
    "FestivalOccurrence",
    "FestivalRule",
    "Paksha",
    "PanchangSource",
    "RegionalVariant",
    "RuleKind",
    "make_panchang_source",
    "resolve_year",
]
