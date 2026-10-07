"""Gateway preserves the PCS canonical interval fields and declares them in OpenAPI."""

from datetime import date

import pytest
from panchang.compute import compute_panchang
from panchang.models import PanchangRequest
from pydantic import ValidationError

from api.cache import panchang_cache_key
from api.main import app
from api.models.panchang import DailyPanchangOut, PeriodOut
from api.panchang_view import to_daily_panchang_view


def test_real_pcs_payload_round_trips_gateway_and_cache_shape() -> None:
    result = compute_panchang(
        PanchangRequest(date=date(2024, 1, 15), lat=28.6139, lon=77.209, tz="Asia/Kolkata")
    )
    payload = result.model_dump(mode="json", by_alias=True)
    out = DailyPanchangOut.model_validate({**payload.pop("request"), **payload})
    serialized = out.model_dump(mode="json", by_alias=True)
    assert serialized["tithi"][0]["startUtc"] == result.tithi[0].start_utc.isoformat().replace(
        "+00:00", "Z"
    )
    assert serialized["muhurat"][0]["hoursFromSunrise"] < 24
    assert DailyPanchangOut.model_validate(serialized) == out


def test_view_does_not_claim_synthetic_sunrise_is_observed() -> None:
    result = compute_panchang(
        PanchangRequest(date=date(2024, 6, 21), lat=78.2, lon=15.6, tz="Arctic/Longyearbyen")
    )
    payload = result.model_dump(mode="json", by_alias=True)
    out = DailyPanchangOut.model_validate({**payload.pop("request"), **payload})
    view = to_daily_panchang_view(out)
    assert "sunriseFallback" in view.flags
    assert "sunriseFallbackNearestValidLatitude" in view.flags
    assert "polarDay" in view.flags
    assert view.sunrise is None
    assert view.sunset is None


def test_partial_new_interval_is_rejected_but_legacy_without_fields_is_accepted() -> None:
    legacy = {
        "name": "Hora",
        "start": {"iso": "a", "hour_24": "a", "hour_12": "a", "hour_24_plus": "a"},
        "end": {"iso": "b", "hour_24": "b", "hour_12": "b", "hour_24_plus": "b"},
    }
    assert PeriodOut.model_validate(legacy).start_utc is None
    with pytest.raises(ValidationError):
        PeriodOut.model_validate({**legacy, "startUtc": "2024-01-01T00:00:00Z"})


def test_public_openapi_exposes_camel_case_interval_fields() -> None:
    schemas = app.openapi()["components"]["schemas"]
    for name in ("AngaSpanOut", "PeriodOut", "ChoghadiyaOut"):
        schema = schemas[name]
        assert "startUtc" in schema["properties"]
        assert "endUtc" in schema["properties"]
        assert "hoursFromSunrise" in schema["properties"]
        assert "localOffsetMinutes" in schema["properties"]
        assert "flags" in schema["properties"]


def test_gateway_cache_key_does_not_reuse_pre_fallback_policy_entries() -> None:
    key = panchang_cache_key("2024-01-15", 28.6, 77.2, "Asia/Kolkata", "lahiri", "amanta")
    assert key.startswith("panchang:canonical-v3:")
