"""Background worker entrypoint.

Starts the RQ/Arq worker process that drains the pdf, reminders, and
cache-warm queues.  Run via:
  python -m api.worker

The WORKER_QUEUES env var (comma-separated) controls which queues this
worker instance handles.  Defaults to all queues.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def main() -> None:
    queues_raw = os.environ.get("WORKER_QUEUES", "pdf,reminders,cache-warm")
    queues = [q.strip() for q in queues_raw.split(",") if q.strip()]

    logger.info("Starting worker for queues: %s", queues)

    try:
        # Prefer arq if available, fall back to rq
        from arq import run_worker  # type: ignore[import]
        from api.pdf.worker import WorkerSettings  # type: ignore[attr-defined]

        run_worker(WorkerSettings)
    except ImportError:
        try:
            from rq import Queue, Worker  # type: ignore[import]
            from redis import Redis  # type: ignore[import]
            from api.settings import get_settings

            settings = get_settings()
            conn = Redis.from_url(settings.redis_url)
            rq_queues = [Queue(name, connection=conn) for name in queues]
            worker = Worker(rq_queues, connection=conn)
            worker.work()
        except ImportError:
            logger.warning(
                "Neither arq nor rq is installed — worker is a no-op in this environment."
            )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
