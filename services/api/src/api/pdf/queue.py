"""PDF job queue — in-process implementation.

The JobStore protocol is satisfied by the in-process dict store used in tests
and local dev.  A production deployment replaces this with an RQ/Celery/Arq
backend via dependency injection in the router.

Job lifecycle:  queued → processing → done | failed
"""

from __future__ import annotations

import asyncio
import datetime
import logging
from typing import Protocol

from api.pdf.worker import CalendarJob, run_job

logger = logging.getLogger(__name__)


# ── Domain types ──────────────────────────────────────────────────────────────

class JobRecord:
    __slots__ = ("job_id", "status", "download_url", "created_at", "error")

    def __init__(self, job_id: str) -> None:
        self.job_id = job_id
        self.status = "queued"
        self.download_url: str | None = None
        self.created_at = datetime.datetime.now(datetime.UTC)
        self.error: str | None = None


# ── JobStore protocol ─────────────────────────────────────────────────────────

class JobStore(Protocol):
    def create(self, job_id: str) -> JobRecord: ...
    def get(self, job_id: str) -> JobRecord | None: ...
    def update(self, record: JobRecord) -> None: ...


# ── In-process implementation (dev / test) ────────────────────────────────────

class InProcessJobStore:
    def __init__(self) -> None:
        self._store: dict[str, JobRecord] = {}

    def create(self, job_id: str) -> JobRecord:
        rec = JobRecord(job_id)
        self._store[job_id] = rec
        return rec

    def get(self, job_id: str) -> JobRecord | None:
        return self._store.get(job_id)

    def update(self, record: JobRecord) -> None:
        self._store[record.job_id] = record

    def clear(self) -> None:
        self._store.clear()


# ── StorageBackend protocol ───────────────────────────────────────────────────

class StorageBackend(Protocol):
    async def put(self, key: str, data: bytes) -> str:
        """Store *data* under *key* and return a signed/direct download URL."""
        ...


# ── Local filesystem storage (dev / test) ─────────────────────────────────────

import tempfile
import os


class LocalFileStorage:
    """Writes PDFs to a temp directory; returns a file:// URL for tests."""

    def __init__(self, base_dir: str | None = None) -> None:
        self._dir = base_dir or tempfile.mkdtemp(prefix="pandit-pdf-")

    async def put(self, key: str, data: bytes) -> str:
        safe_key = key.replace("/", "_")
        path = os.path.join(self._dir, safe_key)
        with open(path, "wb") as f:
            f.write(data)
        return f"file://{path}"

    @property
    def base_dir(self) -> str:
        return self._dir


# ── S3 storage (production) ───────────────────────────────────────────────────

class S3Storage:
    """Writes PDFs to S3-compatible object storage and returns a presigned URL.

    Requires aiobotocore (or boto3 in a sync executor) — installed in prod only.
    Import is deferred so the module loads in test environments without boto3.
    """

    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        presign_expires: int = 3600,
    ) -> None:
        self._endpoint = endpoint_url
        self._access_key = access_key
        self._secret_key = secret_key
        self._bucket = bucket
        self._presign_expires = presign_expires

    async def put(self, key: str, data: bytes) -> str:
        import boto3  # type: ignore[import-untyped]
        from botocore.config import Config  # type: ignore[import-untyped]

        loop = asyncio.get_running_loop()

        def _upload() -> str:
            client = boto3.client(
                "s3",
                endpoint_url=self._endpoint,
                aws_access_key_id=self._access_key,
                aws_secret_access_key=self._secret_key,
                config=Config(signature_version="s3v4"),
            )
            client.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType="application/pdf")
            return client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=self._presign_expires,
            )

        return await loop.run_in_executor(None, _upload)


# ── Singletons (replaced in tests via dependency injection) ───────────────────

_default_store = InProcessJobStore()
_default_storage = LocalFileStorage()


def get_job_store() -> InProcessJobStore:
    return _default_store


def get_storage() -> LocalFileStorage:
    return _default_storage


# ── Queue processor ───────────────────────────────────────────────────────────

async def process_job(
    job: CalendarJob,
    store: JobStore,
    storage: StorageBackend,
) -> None:
    """Fetch, render and store the PDF for *job*.  Updates *store* throughout."""
    rec = store.get(job.job_id)
    if rec is None:
        return

    rec.status = "processing"
    store.update(rec)

    try:
        pdf_bytes = await asyncio.get_running_loop().run_in_executor(None, run_job, job)
        key = f"calendars/{job.job_id}/calendar-{job.year}.pdf"
        url = await storage.put(key, pdf_bytes)
        rec.status = "done"
        rec.download_url = url
    except Exception as exc:
        logger.exception("PDF job %s failed", job.job_id)
        rec.status = "failed"
        rec.error = str(exc)

    store.update(rec)
