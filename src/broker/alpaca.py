from core.config import settings
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

client = TradingClient(
    api_key=settings.alpaca_api_key,
    secret_key=settings.alpaca_secret_key,
    paper=settings.alpaca_paper,
)


def get_positions(client: TradingClient):
    positions = client.get_all_positions
    return positions


def get_account(client: TradingClient):
    account = client.get_account()
    return account
