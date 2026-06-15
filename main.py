import uvicorn
from fastapi import FastAPI
from core.logger_config import setup_logging
from db.startup import db_startup

app = FastAPI()


@app.on_event("startup")
async def startup():
    setup_logging()
    await db_startup()


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
