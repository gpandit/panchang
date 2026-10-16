#!/usr/bin/env python3
"""Check container/build contracts without building or contacting registries.

Set ``PANCHANG_RUN_DOCKER_BUILDS=1`` to additionally build the API and web
images locally.  The optional builds are intentionally separate from the
offline checks because Docker availability and image pulls are environment
concerns, not repository credentials.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def assert_build_contract() -> None:
    api = (ROOT / "services/api/Dockerfile").read_text()
    panchang = (ROOT / "services/panchang/Dockerfile").read_text()
    web = (ROOT / "apps/web/Dockerfile").read_text()
    admin = (ROOT / "apps/admin/Dockerfile").read_text()
    temple_admin = (ROOT / "apps/temple-admin/Dockerfile").read_text()
    staging_deploy = (ROOT / ".github/workflows/staging-deploy.yml").read_text()
    assert "FROM python:3.12-slim" in api
    assert "FROM python:3.12-slim" in panchang
    assert "FROM node:20-alpine" in web
    assert "FROM node:20-alpine" in admin
    assert "FROM node:20-alpine" in temple_admin
    assert "USER api" in api
    assert "USER nextjs" in web
    assert 'output: "standalone"' in (ROOT / "apps/web/next.config.ts").read_text()
    assert "/healthz" in api
    assert "/api/healthz" in web
    assert "/health" in panchang
    assert "/healthz" in admin
    assert "/healthz" in temple_admin
    for image in (
        "pandit-api",
        "pandit-panchang",
        "pandit-web",
        "pandit-admin",
        "pandit-temple-admin",
    ):
        assert f"name: {image}" in staging_deploy, (
            f"staging deploy does not build the {image} image"
        )

    for package in (
        "apps/web/package.json",
        "apps/admin/package.json",
        "apps/temple-admin/package.json",
    ):
        text = (ROOT / package).read_text()
        assert '"build"' in text, f"{package} has no build script"


def build_images() -> None:
    if os.environ.get("PANCHANG_RUN_DOCKER_BUILDS") != "1":
        return
    for dockerfile, tag in (
        ("services/api/Dockerfile", "the-pandit-api:contract-test"),
        ("services/panchang/Dockerfile", "the-pandit-panchang:contract-test"),
        ("apps/web/Dockerfile", "the-pandit-web:contract-test"),
        ("apps/admin/Dockerfile", "the-pandit-admin:contract-test"),
        ("apps/temple-admin/Dockerfile", "the-pandit-temple-admin:contract-test"),
    ):
        subprocess.run(
            ["docker", "build", "--file", dockerfile, "--tag", tag, "."],
            cwd=ROOT,
            check=True,
        )


def main() -> int:
    assert_build_contract()
    build_images()
    print("build contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
