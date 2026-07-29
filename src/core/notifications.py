import json
import urllib.request

from core.config import settings
from core.logger_config import logger

DISCORD_WEBHOOK_URL = settings.discord_webhook_url


def notify(message: str) -> None:
    if not DISCORD_WEBHOOK_URL:
        return

    payload = json.dumps({"content": message}).encode()
    req = urllib.request.Request(
        DISCORD_WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        logger.warning(f"Discord notification failed: {e}")
