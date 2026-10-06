"""Contract guardrails for the aspirational v1 OpenAPI reconciliation."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[3]
INVENTORY = ROOT / "docs" / "openapi-v1-reconciliation.json"


def test_reconciliation_inventory_is_explicit_about_planned_operations() -> None:
    inventory = json.loads(INVENTORY.read_text())
    operations = inventory["runtime_operations"]

    assert inventory["status"] == "runtime-inventory"
    assert inventory["aspirational_counts"] == {"paths": 145, "operations": 172}
    assert inventory["rule"].startswith("An aspirational path/operation is planned")
    assert all(item["method"] in {"GET", "POST", "PUT", "PATCH", "DELETE"} for item in operations)
    assert {item["status"] for item in operations} <= {"implemented", "partial", "planned"}

    # A route registered only as a placeholder must never be silently promoted to shipped.
    planned = {(item["path"], item["method"]) for item in operations if item["status"] == "planned"}
    assert ("/v1/notes", "POST") in planned
    assert ("/v1/reminders", "POST") in planned
    assert ("/v1/profile", "PUT") in planned


def test_legacy_openapi_snapshot_links_to_reconciliation() -> None:
    snapshot = json.loads((ROOT / "docs" / "openapi.json").read_text())
    assert snapshot["info"]["x-contract-status"] == "legacy-runtime-snapshot"
    assert snapshot["info"]["x-reconciliation"] == "openapi-v1-reconciliation.md"


def test_inventory_matches_registered_public_v1_routes() -> None:
    """The reconciliation must fail when a public route is added without review."""
    from api.main import app

    inventory = json.loads(INVENTORY.read_text())
    documented = {
        (item["path"], item["method"]) for item in inventory["runtime_operations"]
    }
    registered = {
        (route.path, method)
        for route in app.routes
        if route.path.startswith("/v1/")
        for method in (route.methods or set())
        if method in {"GET", "POST", "PUT", "PATCH", "DELETE"}
    }

    assert registered == documented
