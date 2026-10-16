"""Tests for versioned festival-rule loading and resolution."""

import json
from dataclasses import FrozenInstanceError
from datetime import date, timedelta
from pathlib import Path

import pytest

from panchang.compute import compute_panchang
from panchang.models import PanchangRequest
from panchang.rules import FestivalRule, RuleCatalog, resolve_festival_range, resolve_festivals

RULES = Path(__file__).resolve().parents[3] / "docs/architecture/the-pandit-festival-rules-v1.json"
DELHI = {"lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata"}


def test_catalog_loads_versioned_rules_and_recurring_cycles() -> None:
    catalog = RuleCatalog.load(RULES)

    assert catalog.version == "1.0.0"
    assert catalog.rules
    assert len({rule.id for rule in catalog.rules}) == len(catalog.rules)
    assert "cycle_ekadashi" in {rule.id for rule in catalog.rules}
    assert "makar_sankranti" in {rule.id for rule in catalog.rules}


def test_catalog_rejects_duplicate_rule_ids(tmp_path: Path) -> None:
    source = RULES.read_text(encoding="utf-8")
    payload = source.replace('"cycle_ekadashi"', '"makar_sankranti"', 1)
    path = tmp_path / "duplicate.json"
    path.write_text(payload, encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate rule ids"):
        RuleCatalog.load(path)


def test_resolver_matches_a_rule_from_the_computed_panchang_day() -> None:
    catalog = RuleCatalog.load(RULES)
    result = compute_panchang(PanchangRequest(date=date(2024, 1, 15), **DELHI))

    # Build a synthetic catalog rule from the actual Swiss result so this test
    # verifies resolution without asserting a published festival date.
    month = result.calendrical.lunar_month.lower()
    tithi_name = result.tithi[0].name
    tithi = {"Purnima": 15, "Amavasya": 30}.get(tithi_name)
    if tithi is None:
        names = [
            "Pratipada",
            "Dwitiya",
            "Tritiya",
            "Chaturthi",
            "Panchami",
            "Shashthi",
            "Saptami",
            "Ashtami",
            "Navami",
            "Dashami",
            "Ekadashi",
            "Dwadashi",
            "Trayodashi",
            "Chaturdashi",
        ]
        paksha, ordinal = tithi_name.split()
        tithi = names.index(ordinal) + 1 + (15 if paksha == "Krishna" else 0)
    rule = FestivalRule(
        id="synthetic_matching_rule",
        name="Synthetic matching rule",
        type="lunar",
        anchor="sunrise",
        tie_break="udaya_tithi",
        regions=("default",),
        priority=1,
        month=month,
        paksha="shukla" if tithi <= 15 else "krishna",
        tithi=tithi,
    )
    occurrences = resolve_festivals(
        result,
        RuleCatalog(
            version=catalog.version,
            review_state=catalog.review_state,
            source=catalog.source,
            rules=(rule,),
            path=catalog.path,
        ),
        include_unpublished=True,
    )

    assert len(occurrences) == 1
    assert occurrences[0].rule_id == rule.id
    assert occurrences[0].rule_version == "1.0.0"


def test_missing_rule_file_is_explicit(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="not found"):
        RuleCatalog.load(tmp_path / "missing.json")


def _days(start: date, count: int, **extra: object) -> list:
    return [
        compute_panchang(PanchangRequest(date=start + timedelta(days=i), **DELHI, **extra))
        for i in range(count)
    ]


def _published(*rules: FestivalRule) -> RuleCatalog:
    return RuleCatalog("test-1", "published", "PCS regression", rules, RULES)


def test_draft_is_editor_preview_only_and_loaded_rules_are_immutable() -> None:
    catalog = RuleCatalog.load(RULES)
    day = _days(date(2024, 1, 15), 1)[0]
    assert resolve_festivals(day, catalog) == []
    with pytest.raises(FrozenInstanceError):
        catalog.version = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError):
        catalog.rules[0].aliases["tamil"] = "changed"  # type: ignore[index]
    with pytest.raises(TypeError):
        catalog.rules[0].overrides[0]["name"] = "changed"  # type: ignore[index]


def test_real_pcs_solar_ingress_exact_instant_and_regional_alias() -> None:
    catalog = RuleCatalog.load(RULES)
    days = _days(date(2024, 1, 13), 4)
    assert resolve_festival_range(days, catalog, region="tamil") == []
    result = resolve_festival_range(
        days,
        catalog,
        region="tamil",
        year=2024,
        month=1,
        location_grid="28.6:77.2:Asia/Kolkata",
        include_unpublished=True,
    )
    sankranti = next(o for o in result if o.rule_id == "makar_sankranti")
    assert sankranti.name == "Thai Pongal"
    assert sankranti.date == date(2024, 1, 15)
    assert sankranti.anchor_utc is not None
    assert sankranti.anchor_utc < days[1].vara.end_utc
    assert sankranti.anchor_utc > days[1].vara.start_utc
    assert sankranti.year == 2024
    assert sankranti.rule_version == "1.0.0"
    assert sankranti.location_grid == "28.6:77.2:Asia/Kolkata"
    assert "after-sunset" in sankranti.explanation
    assert not resolve_festival_range(days, catalog, year=2025, include_unpublished=True)
    assert not resolve_festival_range(days, catalog, month=2, include_unpublished=True)


def test_real_pcs_recurring_tithi_deduplication_and_anchor_provenance() -> None:
    catalog = RuleCatalog.load(RULES)
    days = _days(date(2024, 1, 10), 13)
    result = resolve_festival_range(days, catalog, include_unpublished=True)
    amavasya = [o for o in result if o.rule_id == "cycle_amavasya"]
    assert [o.date for o in amavasya] == [date(2024, 1, 11)]
    assert amavasya[0].anchor_utc is not None
    assert "exact anchor" in amavasya[0].explanation
    assert result == resolve_festival_range(days[::-1], catalog, include_unpublished=True)
    with pytest.raises(ValueError, match="consecutive"):
        resolve_festival_range(days[::2], catalog, include_unpublished=True)


def test_anchor_compares_exact_instant_not_presence_somewhere_in_day() -> None:
    days = _days(date(2024, 1, 10), 4)
    rule = FestivalRule(
        "anchor_probe",
        "Anchor probe",
        "lunar",
        "sunrise",
        "tithi_at_anchor_strict",
        ("default",),
        10,
        tithi=30,
        paksha="krishna",
    )
    result = resolve_festival_range(days, _published(rule))
    assert [o.date for o in result] == [date(2024, 1, 11)]
    assert result[0].anchor_utc == days[1].vara.start_utc


def test_scheme_conversion_applies_to_krishna_month_without_recomputing_pcs() -> None:
    days = _days(date(2024, 1, 10), 3)
    rule = FestivalRule(
        "scheme_probe",
        "Scheme probe",
        "lunar",
        "sunrise",
        "udaya_tithi",
        ("default",),
        10,
        scheme="purnimanta",
        month="pausha",
        paksha="krishna",
        tithi=30,
    )
    output = resolve_festival_range(days, _published(rule))
    assert [o.date for o in output] == [date(2024, 1, 11)]


def test_catalog_rejects_unvalidated_regional_overrides(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text(
        '{"version":"1","reviewState":"published","rules":[{"id":"x","name":"X",'
        '"type":"lunar","anchor":"sunrise","tieBreak":"udaya_tithi",'
        '"regions":["default"],"priority":1,"tithi":1,'
        '"overrides":[{"region":"north","tieBreak":"made_up"}]}]}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=r"overrides.*tieBreak"):
        RuleCatalog.load(path)


@pytest.mark.parametrize(
    ("rule_edit", "message"),
    [
        (lambda rule: rule.update(extra="ignored"), "unsupported keys"),
        (lambda rule: rule.update(id="Not-Copy-Safe"), "lowercase"),
    ],
)
def test_catalog_rejects_unvalidated_rule_shape(tmp_path: Path, rule_edit, message) -> None:
    payload = {
        "version": "1",
        "reviewState": "published",
        "rules": [
            {
                "id": "valid_rule",
                "name": "Valid rule",
                "type": "lunar",
                "anchor": "sunrise",
                "tieBreak": "udaya_tithi",
                "regions": ["default"],
                "priority": 1,
                "tithi": 1,
            }
        ],
    }
    rule_edit(payload["rules"][0])
    path = tmp_path / "invalid-rule.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        RuleCatalog.load(path)
