"""In-memory CMS content store for festival/vrat editorial data.

The CMS holds the editorial content (body prose, puja instructions, katha text,
region/locale tags, publish status) that accompanies each festival.  In this
step the store is backed by an in-process dict; a future step will wire it to
the PostgreSQL content table and Directus/Payload CMS API.

The store is populated by seed data at import time so that tests and local dev
have content to render without an external dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FestivalContent:
    id: str
    slug: str
    name: str
    # "YYYY-MM-DD" or empty when date comes from the rule engine
    date: str
    description: str | None
    # Full rich prose rendered as plain text (HTML sanitisation happens at the
    # presentation layer).
    body: str | None
    # Puja vidhi / instructions (multi-paragraph plain text)
    puja: str | None
    # Katha / story text
    katha: str | None
    tags: list[str] = field(default_factory=list)
    region: str | None = None     # e.g. "all", "north", "south", "west", "east"
    locale: str | None = None     # BCP-47 e.g. "hi", "en", "gu", "mr"
    # Only "published" items are returned by the public API
    status: str = "published"     # "published" | "draft"


# ── Seed data — enough for tests and local dev ────────────────────────────────

_SEED: list[FestivalContent] = [
    FestivalContent(
        id="fest-diwali",
        slug="diwali",
        name="Diwali",
        date="",
        description="Festival of lights celebrating the return of Lord Rama.",
        body=(
            "Diwali, the Festival of Lights, is one of the most significant "
            "celebrations in the Hindu calendar. It marks the return of Lord Rama "
            "to Ayodhya after his 14-year exile and the defeat of the demon king "
            "Ravana. Homes are lit with diyas (oil lamps) and decorated with "
            "rangoli to welcome Goddess Lakshmi."
        ),
        puja=(
            "Lakshmi Puja is performed on the main night of Diwali.\n\n"
            "1. Clean the puja space and set up the idol or image of Goddess Lakshmi.\n"
            "2. Light a ghee diya and offer flowers, incense and sweets.\n"
            "3. Recite the Lakshmi Ashtottara Shatanama Stotram.\n"
            "4. Offer naivedya (prasad) and distribute it to family members."
        ),
        katha=(
            "Long ago, when the world was shrouded in poverty and ignorance, "
            "the gods and demons churned the ocean of milk to obtain Amrita, the "
            "nectar of immortality. From that cosmic ocean arose Goddess Lakshmi, "
            "radiant with grace, bearing lotus flowers and showering blessings upon "
            "all creation. From that day she is worshipped on the night of Diwali."
        ),
        tags=["festival", "lakshmi", "lights"],
        region="all",
        locale="en",
        status="published",
    ),
    FestivalContent(
        id="fest-holi",
        slug="holi",
        name="Holi",
        date="",
        description="Festival of colors celebrating the arrival of spring.",
        body=(
            "Holi is the festival of colors, marking the arrival of spring and the "
            "victory of good over evil through the story of Prahlad and Holika. "
            "People celebrate by smearing each other with colored powders and water."
        ),
        puja=(
            "Holika Dahan (bonfire) is performed the evening before Holi.\n\n"
            "1. Gather dry wood, cow dung cakes and a Holika effigy.\n"
            "2. Light the bonfire after sunset during the auspicious muhurat.\n"
            "3. Circumambulate the fire five times while chanting prayers.\n"
            "4. Offer coconut and prasad to the fire."
        ),
        katha=(
            "Hiranyakashipu, the demon king, demanded that all worship him alone. "
            "His son Prahlad remained devoted to Lord Vishnu. Hiranyakashipu asked "
            "his sister Holika to sit with Prahlad in a bonfire, using her boon of "
            "immunity from fire. But Holika burned while Prahlad was protected by "
            "Vishnu's grace — signifying the triumph of devotion over tyranny."
        ),
        tags=["festival", "spring", "colors"],
        region="all",
        locale="en",
        status="published",
    ),
    FestivalContent(
        id="fest-ekadashi-draft",
        slug="ekadashi-draft",
        name="Draft Ekadashi",
        date="",
        description="A draft festival not yet published.",
        body=None,
        puja=None,
        katha=None,
        tags=["ekadashi"],
        region="all",
        locale="en",
        status="draft",
    ),
    FestivalContent(
        id="fest-navratri",
        slug="navratri",
        name="Navratri",
        date="",
        description="Nine nights of worship of Goddess Durga.",
        body=(
            "Navratri ('nine nights') is celebrated twice a year — in Chaitra "
            "(spring) and Ashwin (autumn). Each of the nine days is dedicated to one "
            "of the nine forms of Goddess Durga. Devotees observe fasts, perform "
            "Garba dances and offer special prayers."
        ),
        puja=(
            "Navratri Puja — Day 1 (Shailaputri):\n\n"
            "1. Set up the Kalash (sacred pot) representing Devi's presence.\n"
            "2. Sow barley seeds in a small clay pot (jawara).\n"
            "3. Recite Durga Saptashati.\n"
            "4. Offer red flowers to the Goddess."
        ),
        katha=(
            "The demon Mahishasura had obtained a boon making him invincible to all "
            "men and gods. When his army terrorized the heavens, the gods combined "
            "their divine powers into a single radiant form — the Goddess Durga. "
            "Over nine nights she battled his forces and on the tenth day (Vijayadashami) "
            "she slew Mahishasura, restoring cosmic order."
        ),
        tags=["festival", "durga", "vrat"],
        region="all",
        locale="en",
        status="published",
    ),
]

_store: dict[str, FestivalContent] = {f.id: f for f in _SEED}


# ── Public API ────────────────────────────────────────────────────────────────

def list_festivals(
    *,
    region: str | None = None,
    locale: str | None = None,
    published_only: bool = True,
) -> list[FestivalContent]:
    results = list(_store.values())
    if published_only:
        results = [f for f in results if f.status == "published"]
    if region:
        results = [f for f in results if f.region in (region, "all", None)]
    if locale:
        results = [f for f in results if f.locale in (locale, None)]
    return results


def get_festival(festival_id: str, *, published_only: bool = True) -> FestivalContent | None:
    item = _store.get(festival_id)
    if item is None:
        return None
    if published_only and item.status != "published":
        return None
    return item


def upsert_festival(content: FestivalContent) -> None:
    """Insert or replace a festival entry (used by tests and admin flows)."""
    _store[content.id] = content
