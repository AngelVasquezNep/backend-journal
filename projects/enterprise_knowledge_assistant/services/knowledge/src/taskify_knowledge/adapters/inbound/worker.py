"""Durable Knowledge worker uses narrow claims, short heartbeats and fenced whole-revision recovery."""

import threading
import time

from taskify_knowledge.application.process_ingestion import process
from taskify_knowledge.application.service import KnowledgeService
from taskify_knowledge.domain.ingestion_job import IngestionJob


class IngestionWorker:
    """Claim outside provider work and heartbeat every eight seconds under the 120-second lease."""

    def __init__(self, service: KnowledgeService) -> None:
        """Retain owned ports and a random worker identity; no public seed/auth bypass is created."""
        self.service = service
        self.worker_id = service.ids.new()

    def claim(self) -> IngestionJob | None:
        """Claim queued/expired work and release database locks before extraction or network activity."""
        return self.service.store.claim(self.worker_id, self.service.clock.now())

    def process(self, job: IngestionJob) -> bool:
        """Process a supplied stored claim; final application/database fences reject stale attempts."""
        return process(self.service, job)

    def run_once(self) -> bool:
        """Process at most one job with a bounded heartbeat; return whether work was claimed."""
        job = self.claim()
        if job is None:
            return False
        finished = threading.Event()

        def heartbeat() -> None:
            """Extend only the current live lease; a failed/stale heartbeat never authorizes publication."""
            while not finished.wait(8):
                try:
                    if not self.service.store.heartbeat(job, self.service.clock.now()):
                        return
                except Exception:
                    return

        thread = threading.Thread(target=heartbeat, daemon=True)
        thread.start()
        try:
            self.process(job)
        finally:
            finished.set()
            thread.join(timeout=1)
        return True


def main() -> None:
    """Run the owning durable queue; restart/reclaim work rather than retaining in-memory job state."""
    from taskify_knowledge.adapters.outbound.operational import configure_logging
    from taskify_knowledge.bootstrap import create_service

    configure_logging()

    worker = IngestionWorker(create_service(worker=True))
    next_cleanup = 0.0
    while True:
        if time.monotonic() >= next_cleanup:
            from taskify_knowledge.application.reconcile_storage import reconcile

            try:
                reconcile(worker.service)
            except Exception:
                pass  # Storage/DB outages leave files private for the next conservative sweep.
            next_cleanup = time.monotonic() + 60
        try:
            if not worker.run_once():
                time.sleep(1)
        except Exception:
            # Durable claims survive storage outages; leave stale work for fenced reclamation.
            time.sleep(1)
