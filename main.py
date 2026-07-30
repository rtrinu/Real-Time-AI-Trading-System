import uvicorn
from fastapi import FastAPI, Depends

from core.startup import startup
from core.shutdown import shutdown
from core.notifications import notify
from core.auth import verify_api_key

app = FastAPI()


@app.on_event("startup")
async def on_startup():
    await startup(app)


@app.on_event("shutdown")
async def on_shutdown():
    notify("🛑 **Server shutting down**")
    await shutdown()


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(news_router, dependencies=[Depends(verify_api_key)])
app.include_router(predict_router, dependencies=[Depends(verify_api_key)])
app.include_router(backtest_router, dependencies=[Depends(verify_api_key)])
app.include_router(monitoring_router, dependencies=[Depends(verify_api_key)])
app.include_router(trade_router, dependencies=[Depends(verify_api_key)])
app.include_router(portfolio_router, dependencies=[Depends(verify_api_key)])
app.include_router(orders_router, dependencies=[Depends(verify_api_key)])

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000)
