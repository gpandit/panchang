"""POST /v1/pdf/jobs — enqueue a 12-month calendar PDF job (Gold tier).
GET  /v1/pdf/jobs/{job_id} — poll job status and retrieve the signed download URL.

The job is processed asynchronously by the PDF worker (Architecture component 06).
Status transitions: queued → processing → done | failed.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, status

from api.dependencies import require_tier
from api.models.auth import SubscriptionTier, TokenClaims
from api.models.common import ApiResponse
from api.models.content import PdfJobIn, PdfJobOut
from api.pdf.queue import (
    InProcessJobStore,
    StorageBackend,
    get_job_store,
    get_storage,
    process_job,
)
from api.pdf.worker import CalendarJob

router = APIRouter(prefix="/pdf", tags=["pdf"])

_gold_dep = require_tier(SubscriptionTier.GOLD)


@router.post("/jobs", response_model=ApiResponse[PdfJobOut], status_code=status.HTTP_202_ACCEPTED)
async def create_pdf_job(
    body: PdfJobIn,
    background_tasks: BackgroundTasks,
    claims: Annotated[TokenClaims, Depends(_gold_dep)],
) -> ApiResponse[PdfJobOut]:
    store: InProcessJobStore = get_job_store()
    storage: StorageBackend = get_storage()

    job_id = str(uuid.uuid4())
    rec = store.create(job_id)

    calendar_job = CalendarJob(
        job_id=job_id,
        year=body.year,
        lat=body.lat,
        lon=body.lon,
        tz=body.tz,
        ayanamsa=body.ayanamsa,
        month_scheme=body.month_scheme,
    )
    background_tasks.add_task(process_job, calendar_job, store, storage)

    return ApiResponse(
        data=PdfJobOut(
            job_id=rec.job_id,
            status=rec.status,
            download_url=rec.download_url,
            created_at=rec.created_at,
        )
    )


@router.get("/jobs/{job_id}", response_model=ApiResponse[PdfJobOut])
async def get_pdf_job(
    job_id: Annotated[str, Path()],
    claims: Annotated[TokenClaims, Depends(_gold_dep)],
) -> ApiResponse[PdfJobOut]:
    store: InProcessJobStore = get_job_store()
    rec = store.get(job_id)
    if rec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return ApiResponse(
        data=PdfJobOut(
            job_id=rec.job_id,
            status=rec.status,
            download_url=rec.download_url,
            created_at=rec.created_at,
        )
    )
