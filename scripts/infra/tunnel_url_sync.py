#!/workspace/.venv/bin/python
"""
tunnel_url_sync — supervisor-managed процесс.
Каждые 30 секунд проверяет лог cloudflared, извлекает
https://*.trycloudflare.com URL и сохраняет в
/workspace/logs/tunnel_url.txt.

Зачем: чтобы URL можно было узнать из лога, и для других
процессов (например webhook setup).

SILENT MODE: только логи.
"""
from __future__ import annotations

import logging
import re
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] tunnel-url-sync: %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("tunnel-url-sync")

CFD_LOG = Path("/workspace/logs/cloudflared.err.log")
CFD_LOG_ALT = Path("/workspace/logs/cloudflared.out.log")
URL_FILE = Path("/workspace/logs/tunnel_url.txt")
PATTERN = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def read_url_from_log() -> str | None:
    for log_path in (CFD_LOG, CFD_LOG_ALT):
        if log_path.exists():
            text = log_path.read_text(errors="ignore")
            matches = PATTERN.findall(text)
            if matches:
                return matches[0]
    return None


def main() -> int:
    log.info("tunnel-url-sync started")
    last_url: str | None = None
    while True:
        url = read_url_from_log()
        if url and url != last_url:
            URL_FILE.write_text(url + "\n")
            log.info("tunnel URL updated: %s", url)
            last_url = url
        elif not url and last_url:
            log.info("tunnel URL lost (cloudflared down?)")
            last_url = None
            URL_FILE.write_text("")
        time.sleep(30)


if __name__ == "__main__":
    main()
