"""POST /v1/pdf/jobs — queue a calendar PDF job (Gold tier).
GET  /v1/pdf/jobs/{job_id} — poll job status and get download URL.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from api.dependencies import require_tier
from api.models.auth import SubscriptionTier, TokenClaims
from api.models.common import ApiResponse
from api.models.content import PdfJobIn, PdfJobOut

router = APIRouter(prefix="/pdf", tags=["pdf"])

_gold_dep = require_tier(SubscriptionTier.GOLD)


@router.post("/jobs", response_model=ApiResponse[PdfJobOut], status_code=status.HTTP_202_ACCEPTED)
async def create_pdf_job(
    body: PdfJobIn,
    claims: Annotated[TokenClaims, Depends(_gold_dep)],
) -> ApiResponse[PdfJobOut]:
    # TODO(step-3.5): enqueue async PDF generation job via the queue service
    job = PdfJobOut(
        job_id=str(uuid.uuid4()),
        status="queued",
        download_url=None,
        created_at=datetime.datetime.now(datetime.UTC),
    )
    return ApiResponse(data=job)


@router.get("/jobs/{job_id}", response_model=ApiResponse[PdfJobOut])
async def get_pdf_job(
    job_id: Annotated[str, Path()],
    claims: Annotated[TokenClaims, Depends(_gold_dep)],
) -> ApiResponse[PdfJobOut]:
    # TODO(step-3.5): look up job from queue/DB
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
