"""Background scheduler worker (整改 R3.6).

A long-running process that periodically ticks the scheduler — the missing
"持续研究" piece between the manual ``POST /tasks/scheduler/tick`` and a full
queue stack (deliberately NOT introduced yet per 整改 §20).

Run standalone:

    python -m scheduler_worker            # uses ASRO_SCHEDULER_INTERVAL (seconds)

Docker: the compose file runs this as the ``scheduler`` service with the
same backend image (``command: python -m scheduler_worker``).
"""

from __future__ import annotations

import os
import signal
import sys
import time

_interval = int(os.environ.get("ASRO_SCHEDULER_INTERVAL", "60"))
_lease = int(os.environ.get("ASRO_SCHEDULER_LEASE", "900"))

_stop = False


def _handle(signum, _frame):
    global _stop
    _stop = True
    print(f"[scheduler] signal {signum} received, shutting down", file=sys.stderr, flush=True)


def main() -> int:
    global _stop
    signal.signal(signal.SIGTERM, _handle)
    signal.signal(signal.SIGINT, _handle)

    from app.db import get_session_factory
    from app.scheduler.scheduler import Scheduler

    print(
        f"[scheduler] started interval={_interval}s lease={_lease}s", flush=True
    )
    while not _stop:
        session = get_session_factory()()
        try:
            result = Scheduler(session).tick()
            if result.claimed or result.recovered:
                print(
                    f"[scheduler] claimed={result.claimed} "
                    f"succeeded={result.succeeded} failed={result.failed} "
                    f"recovered={result.recovered}",
                    flush=True,
                )
            session.commit()
        except Exception as exc:  # noqa: BLE001 — the worker must survive
            session.rollback()
            print(f"[scheduler] tick error: {exc}", file=sys.stderr, flush=True)
        finally:
            session.close()

        # sleep in small steps so shutdown is responsive
        slept = 0.0
        while slept < _interval and not _stop:
            time.sleep(min(1.0, _interval - slept))
            slept += 1.0

    print("[scheduler] stopped", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
