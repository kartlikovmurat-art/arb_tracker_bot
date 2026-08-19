"""Run FastAPI and Telegram bot in one Render web service.

Render's free plan does not support a separate background worker.  The web
process must still bind to $PORT, so uvicorn and the resilient bot supervisor
are launched as sibling subprocesses and stopped together.
"""
from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run_all")


async def main() -> None:
    port = os.getenv("PORT", "8000")
    commands = {
        "api": [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            port,
        ],
        "bot": [sys.executable, "run_bot.py"],
    }
    processes: dict[str, asyncio.subprocess.Process] = {}

    for name, command in commands.items():
        processes[name] = await asyncio.create_subprocess_exec(*command)
        logger.info("Started %s (pid=%s)", name, processes[name].pid)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()

    def request_stop() -> None:
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, request_stop)
        except NotImplementedError:
            pass

    waiters = {
        asyncio.create_task(process.wait()): name
        for name, process in processes.items()
    }
    stop_waiter = asyncio.create_task(stop.wait())
    done, _ = await asyncio.wait(
        [*waiters, stop_waiter],
        return_when=asyncio.FIRST_COMPLETED,
    )

    if not stop.is_set():
        for task in done:
            if task in waiters:
                name = waiters[task]
                logger.error("%s exited with code %s", name, task.result())
                break

    for process in processes.values():
        if process.returncode is None:
            process.terminate()
    await asyncio.gather(
        *(process.wait() for process in processes.values()),
        return_exceptions=True,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
