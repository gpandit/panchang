"""Delivery service — fan-out to APNs / FCM / email.

In production this wraps real push-notification SDKs (APNs via `httpx` JWT
bearer, FCM via Firebase Admin SDK) and an email gateway. In dev/test it logs
to a queue that callers can inspect without network calls.

The interface is intentionally minimal: `DeliveryService.send` accepts one
`OccurrenceRead` and dispatches to every registered channel. The queue layer
(`scheduler.py`) calls this after idempotency is confirmed; the delivery
service itself does not check or write idempotency state.
"""

from __future__ import annotations

import abc
import logging
from collections import deque
from datetime import UTC, datetime

from api.reminders.schemas import OccurrenceRead

log = logging.getLogger(__name__)


class DeliveryChannel(abc.ABC):
    """Abstract base for a single delivery channel (APNs, FCM, email, …)."""

    @abc.abstractmethod
    async def send(self, occurrence: OccurrenceRead, title: str, body: str) -> None: ...


class LoggingChannel(DeliveryChannel):
    """Logs delivery to the standard logger — used in dev and as a fallback."""

    async def send(self, occurrence: OccurrenceRead, title: str, body: str) -> None:
        log.info(
            "REMINDER fire_at=%s key=%s title=%r body=%r",
            occurrence.fire_at.isoformat(),
            occurrence.idempotency_key,
            title,
            body,
        )


class InMemoryChannel(DeliveryChannel):
    """Captures delivered payloads in-process — used in tests.

    Call `channel.delivered` to assert what was sent.
    """

    def __init__(self) -> None:
        self.delivered: deque[dict] = deque()

    async def send(self, occurrence: OccurrenceRead, title: str, body: str) -> None:
        self.delivered.append(
            {
                "idempotency_key": occurrence.idempotency_key,
                "occurrence_date": occurrence.occurrence_date,
                "fire_at": occurrence.fire_at,
                "title": title,
                "body": body,
                "captured_at": datetime.now(tz=UTC),
            }
        )


class StubApnsChannel(DeliveryChannel):
    """Placeholder for the real APNs JWT-bearer push channel.

    Replace the body with `httpx` calls to api.push.apple.com once APNs
    credentials are available (Stage 3 hardening).
    """

    async def send(self, occurrence: OccurrenceRead, title: str, body: str) -> None:
        log.debug("APNs stub — would push key=%s", occurrence.idempotency_key)


class StubFcmChannel(DeliveryChannel):
    """Placeholder for the real FCM push channel.

    Replace with Firebase Admin SDK calls once credentials are available.
    """

    async def send(self, occurrence: OccurrenceRead, title: str, body: str) -> None:
        log.debug("FCM stub — would push key=%s", occurrence.idempotency_key)


class DeliveryService:
    """Fan-out delivery: sends one occurrence to every registered channel.

    Channels are tried independently — a failure in one channel does not
    prevent delivery on others. Errors are logged; the scheduler marks the
    occurrence delivered as long as at least one channel succeeds, or if all
    channels are stubs (no real network calls).
    """

    def __init__(self, channels: list[DeliveryChannel]) -> None:
        self._channels = channels

    async def send(self, occurrence: OccurrenceRead, title: str, body: str) -> None:
        for ch in self._channels:
            try:
                await ch.send(occurrence, title, body)
            except Exception:
                log.exception(
                    "Delivery channel %s failed for key=%s",
                    type(ch).__name__,
                    occurrence.idempotency_key,
                )
