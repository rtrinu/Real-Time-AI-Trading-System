import uvicorn
from fastapi import FastAPI

from core.startup import startup
from core.shutdown import shutdown
from core.notifications import notify
from api.routes.news import router as news_router
from api.routes.predict import router as predict_router
from api.routes.backtest import router as backtest_router
from api.routes.monitoring import router as monitoring_router
from api.routes.trade import router as trade_router
from api.routes.portfolio import router as portfolio_router
from api.routes.orders import router as orders_router

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


app.include_router(news_router)
app.include_router(predict_router)
app.include_router(backtest_router)
app.include_router(monitoring_router)
app.include_router(trade_router)
app.include_router(portfolio_router)
app.include_router(orders_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000)
