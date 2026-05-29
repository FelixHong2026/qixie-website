import json
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx

from app.core.config import settings

# ── Plans ──────────────────────────────────────────────────────────────

PLANS = {
    "monthly": {"price": 9.99, "duration_days": 30, "name": "月卡", "popular": False},
    "quarterly": {"price": 24.99, "duration_days": 90, "name": "季卡", "popular": True},
    "yearly": {"price": 89.99, "duration_days": 365, "name": "年卡", "popular": False},
}


def get_plan(plan_id: str) -> Optional[dict]:
    return PLANS.get(plan_id)


def get_all_plans() -> dict:
    return dict(PLANS)


# ── PayPal REST API Client ─────────────────────────────────────────────

_paypal_base: Optional[str] = None
_access_token: Optional[str] = None
_token_expires_at: float = 0


def _base_url() -> str:
    global _paypal_base
    if _paypal_base is None:
        _paypal_base = (
            "https://api-m.sandbox.paypal.com"
            if settings.paypal_mode == "sandbox"
            else "https://api-m.paypal.com"
        )
    return _paypal_base


async def _get_access_token() -> str:
    global _access_token, _token_expires_at

    now = datetime.now(timezone.utc).timestamp()
    if _access_token and now < _token_expires_at - 60:
        return _access_token

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_base_url()}/v1/oauth2/token",
            auth=(settings.paypal_client_id, settings.paypal_client_secret),
            data={"grant_type": "client_credentials"},
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        _access_token = data["access_token"]
        _token_expires_at = now + data.get("expires_in", 32400)
        return _access_token


async def create_order(plan_id: str, return_url: str, cancel_url: str) -> dict:
    """Create a PayPal order and return the full response."""
    plan = get_plan(plan_id)
    if not plan:
        raise ValueError(f"Unknown plan: {plan_id}")

    token = await _get_access_token()
    amount = f"{plan['price']:.2f}"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_base_url()}/v2/checkout/orders",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "PayPal-Request-Id": f"qixie-{plan_id}-{datetime.now(timezone.utc).timestamp()}",
            },
            json={
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "reference_id": plan_id,
                        "description": f"齐谐中文 {plan['name']}",
                        "amount": {
                            "currency_code": "USD",
                            "value": amount,
                        },
                    }
                ],
                "payment_source": {
                    "paypal": {
                        "experience_context": {
                            "return_url": return_url,
                            "cancel_url": cancel_url,
                        }
                    }
                },
            },
        )
        resp.raise_for_status()
        return resp.json()


async def capture_order(order_id: str) -> dict:
    """Capture an approved PayPal order."""
    token = await _get_access_token()

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_base_url()}/v2/checkout/orders/{order_id}/capture",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        return resp.json()


async def verify_webhook(headers: dict, body: bytes) -> bool:
    """
    Verify PayPal webhook notification using PayPal's REST API
    (POST /v1/notifications/verify-webhook-signature).
    """
    webhook_id = getattr(settings, "paypal_webhook_id", None)
    if not webhook_id:
        return False

    token = await _get_access_token()

    payload = {
        "auth_algo": headers.get("paypal-auth-algo", ""),
        "cert_url": headers.get("paypal-cert-url", ""),
        "transmission_id": headers.get("paypal-transmission-id", ""),
        "transmission_sig": headers.get("paypal-transmission-sig", ""),
        "transmission_time": headers.get("paypal-transmission-time", ""),
        "webhook_id": webhook_id,
        "webhook_event": json.loads(body.decode()) if isinstance(body, bytes) else body,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_base_url()}/v1/notifications/verify-webhook-signature",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if resp.status_code != 200:
            return False
        result = resp.json()
        return result.get("verification_status") == "SUCCESS"


def compute_subscription_expiry(plan_id: str) -> datetime:
    """Compute subscription expiry from now + plan duration."""
    plan = get_plan(plan_id)
    if not plan:
        raise ValueError(f"Unknown plan: {plan_id}")
    return datetime.now(timezone.utc) + timedelta(days=plan["duration_days"])
