def refund_order(order_id, payload, refund_service):
    if not isinstance(payload.get("amount"), int) or payload["amount"] <= 0:
        raise ValueError("positive integer amount required")
    return refund_service.refund(order_id, payload["amount"])
