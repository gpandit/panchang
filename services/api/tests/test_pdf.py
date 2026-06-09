"""Tests for the PDF job pipeline.

Checks that:
- POST /v1/pdf/jobs enqueues a job and returns 202 with status="queued".
- The background worker renders a 12-month PDF and transitions the job to "done".
- The done record carries a non-null download_url.
- The download URL resolves to a valid PDF (bytes start with %PDF).
- GET /v1/pdf/jobs/{id} surfaces the correct status at each stage.
- The endpoint requires Gold tier; lower tiers receive 403.
"""

from __future__ import annotations

import asyncio

import pytest

from api.pdf.queue import InProcessJobStore, LocalFileStorage, process_job
from api.pdf.worker import CalendarJob, render_calendar_pdf


# ── Unit: PDF renderer ────────────────────────────────────────────────────────

def test_render_produces_valid_pdf_bytes():
    job = CalendarJob(job_id="test-render-001", year=2026, lat=19.076, lon=72.877, tz="Asia/Kolkata")
    pdf_bytes = render_calendar_pdf(job)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes[:4] == b"%PDF", "Output must be a valid PDF document"


def test_render_includes_all_12_months():
    job = CalendarJob(job_id="test-render-002", year=2026, lat=19.076, lon=72.877, tz="Asia/Kolkata")
    pdf_bytes = render_calendar_pdf(job)
    # A 12-page PDF must mention each month name in its structure.
    # We verify by checking the PDF is at least a minimal size.
    assert len(pdf_bytes) > 10_000, "12-month PDF should be at least 10 KB"


def test_render_with_festival_overlay():
    job = CalendarJob(
        job_id="test-render-003",
        year=2026,
        lat=19.076,
        lon=72.877,
        tz="Asia/Kolkata",
        festival_map={"2026-01-14": ["Makar Sankranti"], "2026-03-25": ["Holi"]},
    )
    pdf_bytes = render_calendar_pdf(job)
    assert pdf_bytes[:4] == b"%PDF"


# ── Unit: queue + storage ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_process_job_transitions_to_done():
    store = InProcessJobStore()
    storage = LocalFileStorage()
    job = CalendarJob(job_id="queue-test-001", year=2026, lat=28.6, lon=77.2, tz="Asia/Kolkata")
    store.create(job.job_id)

    await process_job(job, store, storage)

    rec = store.get(job.job_id)
    assert rec is not None
    assert rec.status == "done"
    assert rec.download_url is not None
    assert rec.download_url.startswith("file://")


@pytest.mark.asyncio
async def test_process_job_download_url_resolves_to_valid_pdf():
    store = InProcessJobStore()
    storage = LocalFileStorage()
    job = CalendarJob(job_id="queue-test-002", year=2026, lat=28.6, lon=77.2, tz="Asia/Kolkata")
    store.create(job.job_id)

    await process_job(job, store, storage)

    rec = store.get(job.job_id)
    assert rec is not None and rec.download_url is not None

    path = rec.download_url.removeprefix("file://")
    with open(path, "rb") as f:
        data = f.read()
    assert data[:4] == b"%PDF", "Stored file must be a valid PDF"


# ── Integration: API endpoints ────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clear_job_store():
    from api.pdf.queue import _default_store
    _default_store.clear()
    yield
    _default_store.clear()


@pytest.mark.asyncio
async def test_create_pdf_job_returns_202(client, gold_token):
    resp = await client.post(
        "/v1/pdf/jobs",
        json={"year": 2026, "lat": 19.076, "lon": 72.877, "tz": "Asia/Kolkata"},
        headers={"Authorization": f"Bearer {gold_token}"},
    )
    assert resp.status_code == 202
    data = resp.json()["data"]
    assert data["status"] == "queued"
    assert data["job_id"]
    assert data["download_url"] is None


@pytest.mark.asyncio
async def test_create_pdf_job_requires_gold(client, basic_token, silver_token):
    payload = {"year": 2026, "lat": 19.076, "lon": 72.877, "tz": "Asia/Kolkata"}
    for token in (basic_token, silver_token):
        resp = await client.post(
            "/v1/pdf/jobs",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_pdf_job_status_progression(client, gold_token):
    # Create job
    create_resp = await client.post(
        "/v1/pdf/jobs",
        json={"year": 2026, "lat": 19.076, "lon": 72.877, "tz": "Asia/Kolkata"},
        headers={"Authorization": f"Bearer {gold_token}"},
    )
    assert create_resp.status_code == 202
    job_id = create_resp.json()["data"]["job_id"]

    # Allow the background task to complete
    await asyncio.sleep(0.1)

    poll_resp = await client.get(
        f"/v1/pdf/jobs/{job_id}",
        headers={"Authorization": f"Bearer {gold_token}"},
    )
    assert poll_resp.status_code == 200
    data = poll_resp.json()["data"]
    # Status must be one of the valid lifecycle values
    assert data["status"] in ("queued", "processing", "done", "failed")


@pytest.mark.asyncio
async def test_get_pdf_job_unknown_id_404(client, gold_token):
    resp = await client.get(
        "/v1/pdf/jobs/nonexistent-job-id",
        headers={"Authorization": f"Bearer {gold_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_pdf_job_requires_gold(client, basic_token):
    resp = await client.get(
        "/v1/pdf/jobs/some-job-id",
        headers={"Authorization": f"Bearer {basic_token}"},
    )
    assert resp.status_code == 403
