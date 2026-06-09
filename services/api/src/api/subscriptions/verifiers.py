"""Receipt verification for Apple IAP, Google Play Billing, and Stripe.

Each verifier accepts a raw receipt/token from the client and returns a
`VerifiedReceipt` with enough information to write/update the Subscription row.
Clients must never be trusted on tier — it is always derived here.

In production, verifiers call the respective vendor APIs (App Store Server API,
Google Play Developer API, Stripe). In tests, inject a `StaticVerifier` that
returns a pre-configured result without network calls.
"""

from __future__ import annotations

import abc
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

import httpx

from api.subscriptions.models import BillingSource, Tier


@dataclass
class VerifiedReceipt:
    source: BillingSource
    tier: Tier
    provider_subscription_id: str
    expires_at: datetime | None
    # Extra metadata to store (product_id, environment, etc.)
    meta: dict[str, Any]


class ReceiptVerifier(Protocol):
    """Abstract receipt verifier — each billing source implements this."""

    async def verify(self, receipt: str) -> VerifiedReceipt: ...


# ── Product-ID → Tier mapping ─────────────────────────────────────────────────
# These product IDs must match what's configured in App Store Connect /
# Google Play Console / Stripe. They are env-configurable via settings.

_APPLE_PRODUCT_TIERS: dict[str, Tier] = {
    "com.pandit.silver.monthly": Tier.SILVER,
    "com.pandit.silver.annual": Tier.SILVER,
    "com.pandit.gold.monthly": Tier.GOLD,
    "com.pandit.gold.annual": Tier.GOLD,
}

_GOOGLE_PRODUCT_TIERS: dict[str, Tier] = {
    "pandit_silver_monthly": Tier.SILVER,
    "pandit_silver_annual": Tier.SILVER,
    "pandit_gold_monthly": Tier.GOLD,
    "pandit_gold_annual": Tier.GOLD,
}

_STRIPE_PRICE_TIERS: dict[str, Tier] = {
    # Populated at runtime from settings; listed here for documentation.
    # "price_silver_monthly": Tier.SILVER, etc.
}


class VerificationError(Exception):
    """Raised when a receipt cannot be verified or has been tampered with."""


# ── Apple IAP ─────────────────────────────────────────────────────────────────


class AppleIAPVerifier:
    """Verifies Apple App Store receipts via the App Store Server API (v2).

    In sandbox mode (`sandbox=True`), calls the sandbox endpoint.
    The `shared_secret` and `bundle_id` come from the managed secret store
    (API_APPLE_IAP_SHARED_SECRET, API_APPLE_IAP_BUNDLE_ID).
    """

    _PRODUCTION_URL = "https://buy.itunes.apple.com/verifyReceipt"
    _SANDBOX_URL = "https://sandbox.itunes.apple.com/verifyReceipt"

    def __init__(self, shared_secret: str, bundle_id: str, sandbox: bool = False) -> None:
        self._shared_secret = shared_secret
        self._bundle_id = bundle_id
        self._url = self._SANDBOX_URL if sandbox else self._PRODUCTION_URL

    async def verify(self, receipt: str) -> VerifiedReceipt:
        payload = {
            "receipt-data": receipt,
            "password": self._shared_secret,
            "exclude-old-transactions": True,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(self._url, json=payload)
        resp.raise_for_status()
        data = resp.json()

        status = data.get("status", -1)
        # 21007 = receipt sent to prod but is sandbox — retry on sandbox
        if status == 21007:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(self._SANDBOX_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status", -1)

        if status != 0:
            raise VerificationError(f"Apple IAP verification failed: status={status}")

        receipt_info = data.get("receipt", {})
        in_app = data.get("latest_receipt_info") or receipt_info.get("in_app", [])
        if not in_app:
            raise VerificationError("Apple IAP: no in-app purchase info in receipt")

        # Use the most recent active transaction
        latest = max(
            in_app,
            key=lambda t: int(t.get("purchase_date_ms", 0)),
        )
        product_id = latest.get("product_id", "")
        tier = _APPLE_PRODUCT_TIERS.get(product_id)
        if tier is None:
            raise VerificationError(f"Apple IAP: unrecognised product_id={product_id!r}")

        expires_ms = latest.get("expires_date_ms")
        expires_at: datetime | None = None
        if expires_ms:
            expires_at = datetime.fromtimestamp(int(expires_ms) / 1000, tz=UTC)

        return VerifiedReceipt(
            source=BillingSource.APPLE,
            tier=tier,
            provider_subscription_id=latest.get("original_transaction_id", product_id),
            expires_at=expires_at,
            meta={
                "product_id": product_id,
                "bundle_id": self._bundle_id,
                "environment": data.get("environment", "unknown"),
            },
        )


# ── Google Play Billing ───────────────────────────────────────────────────────


class GooglePlayVerifier:
    """Verifies Google Play subscription receipts via the Play Developer API.

    `purchase_token` (receipt) and `package_name`/`product_id` arrive from the
    client. The service account JSON key is loaded from the managed secret store
    (API_GOOGLE_PLAY_SERVICE_ACCOUNT_JSON).

    For simplicity we call the REST endpoint directly with a pre-fetched
    OAuth2 access token (injected via `access_token` for testability).
    """

    _BASE = "https://androidpublisher.googleapis.com/androidpublisher/v3"

    def __init__(
        self,
        package_name: str,
        access_token_provider: AccessTokenProvider,
    ) -> None:
        self._package = package_name
        self._token_provider = access_token_provider

    async def verify(self, receipt: str) -> VerifiedReceipt:
        """receipt is JSON: {"productId": "...", "purchaseToken": "..."}"""
        try:
            payload = json.loads(receipt)
        except json.JSONDecodeError as exc:
            raise VerificationError("Google Play receipt is not valid JSON") from exc

        product_id = payload.get("productId", "")
        purchase_token = payload.get("purchaseToken", "")
        if not product_id or not purchase_token:
            raise VerificationError("Google Play receipt missing productId or purchaseToken")

        tier = _GOOGLE_PRODUCT_TIERS.get(product_id)
        if tier is None:
            raise VerificationError(f"Google Play: unrecognised productId={product_id!r}")

        token = await self._token_provider.get_token()
        url = (
            f"{self._BASE}/applications/{self._package}"
            f"/purchases/subscriptions/{product_id}/tokens/{purchase_token}"
        )
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})

        if resp.status_code == 404:
            raise VerificationError("Google Play: purchase not found")
        resp.raise_for_status()
        data = resp.json()

        # paymentState: 0=pending, 1=received, 2=free trial, 3=deferred
        payment_state = data.get("paymentState", 0)
        if payment_state not in (1, 2):
            raise VerificationError(
                f"Google Play: subscription not paid (paymentState={payment_state})"
            )

        expires_ms = data.get("expiryTimeMillis")
        expires_at: datetime | None = None
        if expires_ms:
            expires_at = datetime.fromtimestamp(int(expires_ms) / 1000, tz=UTC)

        return VerifiedReceipt(
            source=BillingSource.GOOGLE,
            tier=tier,
            provider_subscription_id=data.get("orderId", purchase_token),
            expires_at=expires_at,
            meta={"product_id": product_id, "package_name": self._package},
        )


class AccessTokenProvider(abc.ABC):
    @abc.abstractmethod
    async def get_token(self) -> str: ...


class StaticAccessTokenProvider(AccessTokenProvider):
    def __init__(self, token: str) -> None:
        self._token = token

    async def get_token(self) -> str:
        return self._token


# ── Stripe ────────────────────────────────────────────────────────────────────

_STRIPE_PRODUCT_TIERS: dict[str, Tier] = {}


class StripeVerifier:
    """Verifies a Stripe checkout session or subscription ID.

    receipt is a Stripe subscription ID (sub_xxx) or a checkout session ID
    (cs_xxx). We fetch the subscription object from the Stripe API.

    `api_key` comes from the managed secret store (API_STRIPE_SECRET_KEY).
    `price_tier_map` maps Stripe price IDs to Tier values — configurable via
    settings so it doesn't require code changes when prices are updated.
    """

    _BASE = "https://api.stripe.com/v1"

    def __init__(self, api_key: str, price_tier_map: dict[str, Tier] | None = None) -> None:
        self._api_key = api_key
        self._price_tiers = price_tier_map or {}

    async def verify(self, receipt: str) -> VerifiedReceipt:
        """receipt is a Stripe subscription ID (sub_xxx)."""
        if not receipt.startswith(("sub_", "cs_")):
            raise VerificationError("Stripe receipt must be a subscription or session ID")

        async with httpx.AsyncClient(
            timeout=10,
            auth=(self._api_key, ""),
        ) as client:
            if receipt.startswith("cs_"):
                # Resolve checkout session → subscription
                resp = await client.get(
                    f"{self._BASE}/checkout/sessions/{receipt}",
                    params={"expand[]": "subscription"},
                )
                resp.raise_for_status()
                session_data = resp.json()
                sub = session_data.get("subscription")
                if not sub or isinstance(sub, str):
                    raise VerificationError("Stripe checkout session has no subscription")
                sub_data = sub if isinstance(sub, dict) else {}
                subscription_id = sub_data.get("id", receipt)
            else:
                resp = await client.get(f"{self._BASE}/subscriptions/{receipt}")
                resp.raise_for_status()
                sub_data = resp.json()
                subscription_id = sub_data.get("id", receipt)

        status = sub_data.get("status", "")
        if status not in ("active", "trialing"):
            raise VerificationError(f"Stripe subscription not active: status={status!r}")

        items = sub_data.get("items", {}).get("data", [])
        price_id = items[0]["price"]["id"] if items else ""
        tier = self._price_tiers.get(price_id)
        if tier is None:
            raise VerificationError(f"Stripe: unrecognised price_id={price_id!r}")

        current_period_end = sub_data.get("current_period_end")
        expires_at: datetime | None = None
        if current_period_end:
            expires_at = datetime.fromtimestamp(int(current_period_end), tz=UTC)

        return VerifiedReceipt(
            source=BillingSource.STRIPE,
            tier=tier,
            provider_subscription_id=subscription_id,
            expires_at=expires_at,
            meta={"price_id": price_id, "status": status},
        )


# ── Test double ───────────────────────────────────────────────────────────────


class StaticReceiptVerifier:
    """Returns a pre-configured VerifiedReceipt; used in tests and sandboxing."""

    def __init__(self, result: VerifiedReceipt | None = None, error: str | None = None) -> None:
        self._result = result
        self._error = error

    async def verify(self, receipt: str) -> VerifiedReceipt:
        if self._error:
            raise VerificationError(self._error)
        if self._result is None:
            raise VerificationError("StaticReceiptVerifier: no result configured")
        return self._result
