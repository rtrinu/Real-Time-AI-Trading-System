import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.routes.orders import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.fixture
def mock_alpaca():
    m = MagicMock()
    app.state.alpaca_client = m
    yield m
    app.state.alpaca_client = None


def make_mock_order(
    order_id="ord_1", symbol="AAPL", side="buy", qty="100",
    filled_qty="100", filled_avg_price="150.50", status="filled",
    order_type="market", time_in_force="day",
):
    o = MagicMock()
    o.id = order_id
    o.symbol = symbol
    o.side = MagicMock()
    o.side.value = side
    o.qty = qty
    o.filled_qty = filled_qty
    o.filled_avg_price = filled_avg_price
    o.status = MagicMock()
    o.status.value = status
    o.type = MagicMock()
    o.type.value = order_type
    o.time_in_force = MagicMock()
    o.time_in_force.value = time_in_force
    o.limit_price = None
    o.stop_price = None
    o.created_at = "2026-07-28T00:00:00Z"
    o.submitted_at = "2026-07-28T00:00:00Z"
    o.filled_at = "2026-07-28T00:00:00Z"
    o.expired_at = None
    o.canceled_at = None
    return o


class TestListOrders:
    def test_returns_empty_list(self, mock_alpaca):
        mock_alpaca.get_orders.return_value = []
        response = client.get("/orders")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_orders(self, mock_alpaca):
        mock_alpaca.get_orders.return_value = [make_mock_order()]
        response = client.get("/orders")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "ord_1"
        assert data[0]["symbol"] == "AAPL"
        assert data[0]["side"] == "buy"
        assert data[0]["qty"] == "100"
        assert data[0]["status"] == "filled"

    def test_passes_limit_param(self, mock_alpaca):
        mock_alpaca.get_orders.return_value = []
        response = client.get("/orders?limit=10")
        assert response.status_code == 200
        call_kwargs = mock_alpaca.get_orders.call_args[0][0]
        assert call_kwargs.limit == 10

    def test_passes_side_param(self, mock_alpaca):
        mock_alpaca.get_orders.return_value = []
        response = client.get("/orders?side=sell")
        assert response.status_code == 200
        call_kwargs = mock_alpaca.get_orders.call_args[0][0]
        assert call_kwargs.side == "sell"

    def test_passes_status_open(self, mock_alpaca):
        mock_alpaca.get_orders.return_value = []
        response = client.get("/orders?status=open")
        assert response.status_code == 200
        from alpaca.trading.enums import QueryOrderStatus
        call_kwargs = mock_alpaca.get_orders.call_args[0][0]
        assert call_kwargs.status == QueryOrderStatus.OPEN

    def test_passes_status_closed(self, mock_alpaca):
        mock_alpaca.get_orders.return_value = []
        response = client.get("/orders?status=closed")
        assert response.status_code == 200
        from alpaca.trading.enums import QueryOrderStatus
        call_kwargs = mock_alpaca.get_orders.call_args[0][0]
        assert call_kwargs.status == QueryOrderStatus.CLOSED

    def test_returns_503_when_no_client(self):
        app.state.alpaca_client = None
        response = client.get("/orders")
        assert response.status_code == 503
        assert "not initialized" in response.json()["detail"]
        app.state.alpaca_client = MagicMock()

    def test_returns_502_on_api_error(self, mock_alpaca):
        mock_alpaca.get_orders.side_effect = Exception("API error")
        response = client.get("/orders")
        assert response.status_code == 502
        assert "API error" in response.json()["detail"]

    def test_serializes_all_order_fields(self, mock_alpaca):
        mock_alpaca.get_orders.return_value = [make_mock_order()]
        response = client.get("/orders")
        data = response.json()[0]
        expected_keys = [
            "id", "symbol", "side", "qty", "filled_qty", "filled_avg_price",
            "status", "type", "time_in_force", "limit_price", "stop_price",
            "created_at", "submitted_at", "filled_at", "expired_at", "canceled_at",
        ]
        for key in expected_keys:
            assert key in data


class TestGetOrder:
    def test_returns_order(self, mock_alpaca):
        mock_alpaca.get_order_by_id.return_value = make_mock_order(order_id="ord_42")
        response = client.get("/orders/ord_42")
        assert response.status_code == 200
        assert response.json()["id"] == "ord_42"
        mock_alpaca.get_order_by_id.assert_called_once_with("ord_42")

    def test_returns_503_when_no_client(self):
        app.state.alpaca_client = None
        response = client.get("/orders/ord_42")
        assert response.status_code == 503
        app.state.alpaca_client = MagicMock()

    def test_returns_502_on_api_error(self, mock_alpaca):
        mock_alpaca.get_order_by_id.side_effect = Exception("Not found")
        response = client.get("/orders/invalid")
        assert response.status_code == 502


class TestCancelOrder:
    def test_cancels_order(self, mock_alpaca):
        mock_alpaca.cancel_order_by_id.return_value = None
        response = client.delete("/orders/ord_42")
        assert response.status_code == 200
        assert response.json() == {"order_id": "ord_42", "canceled": True, "result": None}
        mock_alpaca.cancel_order_by_id.assert_called_once_with("ord_42")

    def test_returns_503_when_no_client(self):
        app.state.alpaca_client = None
        response = client.delete("/orders/ord_42")
        assert response.status_code == 503
        app.state.alpaca_client = MagicMock()

    def test_returns_502_on_api_error(self, mock_alpaca):
        mock_alpaca.cancel_order_by_id.side_effect = Exception("Cancel failed")
        response = client.delete("/orders/ord_42")
        assert response.status_code == 502

    def test_returns_result_when_provided(self, mock_alpaca):
        mock_result = MagicMock()
        mock_alpaca.cancel_order_by_id.return_value = mock_result
        response = client.delete("/orders/ord_42")
        assert response.json()["result"] == str(mock_result)


class TestClosePosition:
    def test_closes_position(self, mock_alpaca):
        mock_order = MagicMock()
        mock_order.id = "close_ord_1"
        mock_order.status = "filled"
        mock_alpaca.close_position.return_value = mock_order
        response = client.delete("/positions/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["closed"] is True
        assert data["order_id"] == "close_ord_1"
        mock_alpaca.close_position.assert_called_once_with("AAPL", close_options=None)

    def test_closes_position_with_qty(self, mock_alpaca):
        mock_order = MagicMock()
        mock_order.id = "close_ord_2"
        mock_order.status = "filled"
        mock_alpaca.close_position.return_value = mock_order
        response = client.delete("/positions/AAPL?qty=50")
        assert response.status_code == 200
        args = mock_alpaca.close_position.call_args
        assert args[0][0] == "AAPL"
        assert args[1]["close_options"].qty == "50"

    def test_returns_503_when_no_client(self):
        app.state.alpaca_client = None
        response = client.delete("/positions/AAPL")
        assert response.status_code == 503
        app.state.alpaca_client = MagicMock()

    def test_returns_502_on_api_error(self, mock_alpaca):
        mock_alpaca.close_position.side_effect = Exception("Position not found")
        response = client.delete("/positions/AAPL")
        assert response.status_code == 502


class TestCloseAllPositions:
    def test_closes_all_positions(self, mock_alpaca):
        mock_alpaca.close_all_positions.return_value = ["result1", "result2"]
        response = client.delete("/positions")
        assert response.status_code == 200
        data = response.json()
        assert data["closed"] is True
        assert data["count"] == 2
        mock_alpaca.close_all_positions.assert_called_once_with(cancel_orders=True)

    def test_returns_503_when_no_client(self):
        app.state.alpaca_client = None
        response = client.delete("/positions")
        assert response.status_code == 503
        app.state.alpaca_client = MagicMock()

    def test_returns_502_on_api_error(self, mock_alpaca):
        mock_alpaca.close_all_positions.side_effect = Exception("Close failed")
        response = client.delete("/positions")
        assert response.status_code == 502

    def test_passes_cancel_orders_flag(self, mock_alpaca):
        mock_alpaca.close_all_positions.return_value = []
        response = client.delete("/positions?cancel_orders=false")
        assert response.status_code == 200
        mock_alpaca.close_all_positions.assert_called_once_with(cancel_orders=False)
