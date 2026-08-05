import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from core.auth import verify_api_key
from core.config import settings

app = FastAPI()


@app.get("/protected")
def protected(_: str = Depends(verify_api_key)):
    return {"ok": True}


client = TestClient(app)


@pytest.fixture
def isolated_log(tmp_path, monkeypatch):
    log_path = tmp_path / "access.log"
    monkeypatch.setattr(settings, "auth_log_path", str(log_path))
    return log_path


class TestMissingApiKey:
    def test_missing_header_returns_422(self):
        response = client.get("/protected")
        assert response.status_code == 422


class TestInvalidApiKey:
    def test_invalid_key_returns_401(self, isolated_log):
        response = client.get("/protected", headers={"X-API-Key": "wrong-key"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid API key"

    def test_invalid_key_writes_fail2ban_log(self, isolated_log):
        response = client.get("/protected", headers={"X-API-Key": "wrong-key"})
        assert response.status_code == 401
        assert "FAIL2BAN 401 from" in isolated_log.read_text()

    def test_unwritable_log_still_returns_401(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "auth_log_path", str(tmp_path))
        response = client.get("/protected", headers={"X-API-Key": "wrong-key"})
        assert response.status_code == 401


class TestValidApiKey:
    def test_valid_key_returns_200(self):
        response = client.get("/protected", headers={"X-API-Key": settings.api_key})
        assert response.status_code == 200
        assert response.json() == {"ok": True}
