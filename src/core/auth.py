import logging

from fastapi import Header, HTTPException, Request
from core.config import settings

logger = logging.getLogger("trading-system.auth")


def verify_api_key(x_api_key: str = Header(...), request: Request = None):
    if x_api_key != settings.api_key:
        client = request.client.host if request and request.client else "unknown"
        logger.warning(f"401 from {client} - invalid X-API-Key")
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key
