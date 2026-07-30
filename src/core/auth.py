from fastapi import Header, HTTPException
from core.config import settings


def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.api_key:
        with open("/app/logs/access.log", "a") as f:
            f.write(f"FAIL2BAN 401 from invalid API key\n")
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key
