"""Focused startup and readiness tests for the Panchang service."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest

import panchang.app as service_app


def test_ephemeris_readiness_requires_the_runtime_data_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(service_app.settings, "ephemeris_path", str(tmp_path))
    assert not service_app._ephemeris_ready()

    for filename in ("semo_18.se1", "sepl_18.se1", "seas_18.se1"):
        (tmp_path / filename).touch()
    assert service_app._ephemeris_ready()


@pytest.mark.asyncio
async def test_non_development_lifespan_wires_shared_cache_clients(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RedisFake:
        instances: ClassVar[list[RedisFake]] = []

        def __init__(self, url: str) -> None:
            self.url = url
            self.pinged = False
            self.closed = False
            self.__class__.instances.append(self)

        def ping(self) -> None:
            self.pinged = True

        def close(self) -> None:
            self.closed = True

    class RepositoryFake:
        instances: ClassVar[list[RepositoryFake]] = []

        def __init__(self, url: str) -> None:
            self.url = url
            self.closed = False
            self.__class__.instances.append(self)

        def close(self) -> None:
            self.closed = True

    configured: list[tuple[object, object]] = []
    monkeypatch.setattr(service_app.settings, "environment", "staging")
    monkeypatch.setattr(service_app.settings, "redis_url", "redis://staging/1")
    monkeypatch.setattr(service_app.settings, "database_url", "postgresql://staging/pandit")
    monkeypatch.setattr(
        service_app, "Redis", type("RedisFactory", (), {"from_url": staticmethod(RedisFake)})
    )
    monkeypatch.setattr(service_app, "PostgresCacheRepository", RepositoryFake)
    monkeypatch.setattr(
        service_app,
        "configure_cache",
        lambda redis, repository: configured.append((redis, repository)),
    )

    async with service_app.lifespan(service_app.app):
        assert len(configured) == 1
        assert configured[0][0].pinged
        assert configured[0][0].url == "redis://staging/1"
        assert configured[0][1].url == "postgresql://staging/pandit"

    assert configured[0][0].closed
    assert configured[0][1].closed
