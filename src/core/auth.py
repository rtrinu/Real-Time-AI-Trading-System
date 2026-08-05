from fastapi import Header, HTTPException, Request
from core.config import settings


def verify_api_key(x_api_key: str = Header(...), request: Request = None):
    if x_api_key != settings.api_key:
        client = request.client.host if request and request.client else "unknown"
        try:
            with open(settings.auth_log_path, "a") as f:
                f.write(f"FAIL2BAN 401 from {client}\n")
        except OSError:
            pass
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key
