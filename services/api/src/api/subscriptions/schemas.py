"""Pydantic schemas for subscription API requests and responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from api.subscriptions.entitlements import Feature
from api.subscriptions.models import BillingSource, SubscriptionStatus, Tier


class VerifyReceiptRequest(BaseModel):
    source: BillingSource
    receipt: str  # raw receipt / token / subscription ID from the client


class SubscriptionResponse(BaseModel):
    user_id: str
    tier: Tier
    source: BillingSource | None
    status: SubscriptionStatus
    expires_at: datetime | None
    provider_subscription_id: str | None

    model_config = {"from_attributes": True}


class EntitlementResponse(BaseModel):
    tier: Tier
    limits: dict[str, int | bool]
    features: dict[str, bool]  # boolean feature flags


class EntitlementCheckRequest(BaseModel):
    feature: Feature
    current_count: int = 0  # for quantity features; ignored for boolean features
