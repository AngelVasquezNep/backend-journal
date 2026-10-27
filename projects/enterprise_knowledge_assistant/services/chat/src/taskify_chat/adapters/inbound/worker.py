"""Chat-owned durable workers recover whole turns with bounded leases, heartbeats and concurrency."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from taskify_chat.application.process_turn import process
from taskify_chat.application.service import ChatService


class AnswerWorker:
    """Process one claimed turn per worker task with a 30-second lease and four-second heartbeat."""

    def __init__(self, service: ChatService) -> None:
        """Retain only owned ports and a random worker identifier; no provider graph state is saved."""
        self.service = service
        self.worker_id = service.ids.new()

    def run_once(self) -> bool:
        """Claim in a short transaction, run fresh work, then fence a single terminal commit."""
        turn = self.service.store.claim(self.worker_id, self.service.clock.now())
        if turn is None:
            return False
        stopped = threading.Event()

        def heartbeat() -> None:
            """Stop refreshing failed/expired/stale leases; retain final application checks."""
            while not stopped.wait(4):
                try:
                    if not self.service.store.heartbeat(turn, self.service.clock.now()):
                        return
                except Exception:
                    return

        thread = threading.Thread(target=heartbeat, daemon=True)
        thread.start()
        try:
            process(self.service, turn)
        finally:
            stopped.set()
            thread.join(timeout=1)
        return True


def main() -> None:
    """Support at most 20 simultaneous whole-turn attempts on this initial single host."""
    from taskify_chat.adapters.outbound.operational import configure_logging
    from taskify_chat.bootstrap import create_service

    configure_logging()

    service = create_service(worker=True)

    def loop() -> None:
        """Retain no attempt state between claims; restart all graph nodes after an abandoned lease."""
        worker = AnswerWorker(service)
        while True:
            try:
                if not worker.run_once():
                    time.sleep(0.25)
            except Exception:
                time.sleep(1)

    with ThreadPoolExecutor(max_workers=20) as executor:
        for _ in range(20):
            executor.submit(loop)
