"""Tests: entitlement enforcement on gated endpoints."""

from __future__ import annotations

from httpx import AsyncClient


class TestRemindersSilverGate:
    """Reminders require Silver tier."""

    async def test_basic_tier_denied(self, client: AsyncClient, basic_token: str) -> None:
        response = await client.get(
            "/v1/reminders",
            headers={"Authorization": f"Bearer {basic_token}"},
        )
        assert response.status_code == 403
        body = response.json()
        assert body["detail"]["code"] == "insufficient_tier"

    async def test_silver_tier_allowed(self, client: AsyncClient, silver_token: str) -> None:
        response = await client.get(
            "/v1/reminders",
            headers={"Authorization": f"Bearer {silver_token}"},
        )
        # 200 (empty list) — not 403
        assert response.status_code == 200

    async def test_gold_tier_allowed(self, client: AsyncClient, gold_token: str) -> None:
        response = await client.get(
            "/v1/reminders",
            headers={"Authorization": f"Bearer {gold_token}"},
        )
        assert response.status_code == 200


class TestPdfGoldGate:
    """PDF jobs require Gold tier."""

    async def test_basic_tier_denied(self, client: AsyncClient, basic_token: str) -> None:
        response = await client.post(
            "/v1/pdf/jobs",
            json={
                "year": 2025,
                "month": 1,
                "lat": 28.6139,
                "lon": 77.2090,
                "tz": "Asia/Kolkata",
            },
            headers={"Authorization": f"Bearer {basic_token}"},
        )
        assert response.status_code == 403

    async def test_silver_tier_denied(self, client: AsyncClient, silver_token: str) -> None:
        response = await client.post(
            "/v1/pdf/jobs",
            json={
                "year": 2025,
                "month": 1,
                "lat": 28.6139,
                "lon": 77.2090,
                "tz": "Asia/Kolkata",
            },
            headers={"Authorization": f"Bearer {silver_token}"},
        )
        assert response.status_code == 403

    async def test_gold_tier_allowed(self, client: AsyncClient, gold_token: str) -> None:
        response = await client.post(
            "/v1/pdf/jobs",
            json={
                "year": 2025,
                "month": 1,
                "lat": 28.6139,
                "lon": 77.2090,
                "tz": "Asia/Kolkata",
            },
            headers={"Authorization": f"Bearer {gold_token}"},
        )
        # 202 Accepted — queued
        assert response.status_code == 202


class TestSubscriptionTierMeets:
    """SubscriptionTier.meets() ordering is correct."""

    def test_basic_meets_basic(self) -> None:
        from api.models.auth import SubscriptionTier

        assert SubscriptionTier.BASIC.meets(SubscriptionTier.BASIC)

    def test_basic_does_not_meet_silver(self) -> None:
        from api.models.auth import SubscriptionTier

        assert not SubscriptionTier.BASIC.meets(SubscriptionTier.SILVER)

    def test_gold_meets_all(self) -> None:
        from api.models.auth import SubscriptionTier

        for tier in SubscriptionTier:
            assert SubscriptionTier.GOLD.meets(tier)
