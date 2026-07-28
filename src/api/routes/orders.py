from fastapi import APIRouter, HTTPException, Request, Query
from alpaca.trading.requests import GetOrdersRequest, ClosePositionRequest

router = APIRouter()


def _serialize_order(o):
    return {
        "id": str(o.id),
        "symbol": o.symbol,
        "side": str(o.side.value) if hasattr(o.side, "value") else str(o.side),
        "qty": str(o.qty),
        "filled_qty": str(o.filled_qty) if o.filled_qty else "0",
        "filled_avg_price": str(o.filled_avg_price) if o.filled_avg_price else None,
        "status": str(o.status.value) if hasattr(o.status, "value") else str(o.status),
        "type": str(o.type.value) if hasattr(o.type, "value") else str(o.type),
        "time_in_force": str(o.time_in_force.value) if hasattr(o.time_in_force, "value") else str(o.time_in_force),
        "limit_price": str(o.limit_price) if o.limit_price else None,
        "stop_price": str(o.stop_price) if o.stop_price else None,
        "created_at": str(o.created_at) if o.created_at else None,
        "submitted_at": str(o.submitted_at) if o.submitted_at else None,
        "filled_at": str(o.filled_at) if o.filled_at else None,
        "expired_at": str(o.expired_at) if o.expired_at else None,
        "canceled_at": str(o.canceled_at) if o.canceled_at else None,
    }


@router.get("/orders")
def list_orders(
    request: Request,
    status: str = Query(default=None, description="Filter by status: open, closed, all"),
    limit: int = Query(default=50, le=500),
    side: str = Query(default=None),
):
    client = getattr(request.app.state, "alpaca_client", None)
    if not client:
        raise HTTPException(status_code=503, detail="Alpaca client not initialized")

    filter_status = status if status in ("open", "closed", "all") else None

    try:
        orders = client.get_orders(
            GetOrdersRequest(
                status=filter_status,
                limit=limit,
                side=side,
            )
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch orders: {e}")

    return [_serialize_order(o) for o in orders]


@router.get("/orders/{order_id}")
def get_order(order_id: str, request: Request):
    client = getattr(request.app.state, "alpaca_client", None)
    if not client:
        raise HTTPException(status_code=503, detail="Alpaca client not initialized")

    try:
        order = client.get_order_by_id(order_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch order: {e}")

    return _serialize_order(order)


@router.delete("/orders/{order_id}")
def cancel_order(order_id: str, request: Request):
    client = getattr(request.app.state, "alpaca_client", None)
    if not client:
        raise HTTPException(status_code=503, detail="Alpaca client not initialized")

    try:
        result = client.cancel_order_by_id(order_id)
        return {"order_id": order_id, "canceled": True, "result": str(result) if result else None}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to cancel order: {e}")


@router.delete("/positions/{symbol}")
def close_position(symbol: str, request: Request, qty: str = Query(default=None)):
    client = getattr(request.app.state, "alpaca_client", None)
    if not client:
        raise HTTPException(status_code=503, detail="Alpaca client not initialized")

    try:
        close_options = ClosePositionRequest(qty=qty) if qty else None
        order = client.close_position(symbol, close_options=close_options)
        return {
            "symbol": symbol,
            "closed": True,
            "order_id": str(order.id) if hasattr(order, "id") else None,
            "status": str(order.status) if hasattr(order, "status") else None,
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to close position: {e}")


@router.delete("/positions")
def close_all_positions(request: Request, cancel_orders: bool = Query(default=True)):
    client = getattr(request.app.state, "alpaca_client", None)
    if not client:
        raise HTTPException(status_code=503, detail="Alpaca client not initialized")

    try:
        results = client.close_all_positions(cancel_orders=cancel_orders)
        return {"closed": True, "count": len(results), "results": [str(r) for r in results]}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to close positions: {e}")
