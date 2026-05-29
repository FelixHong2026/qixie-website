from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User, Payment, PaymentStatus
from app.schemas.payment import (
    PlanInfo,
    CreateOrderRequest,
    CreateOrderResponse,
    CaptureOrderRequest,
    CaptureOrderResponse,
    PaymentHistoryItem,
    PaymentHistoryResponse,
)
from app.services.paypal import (
    get_all_plans,
    get_plan,
    create_order as paypal_create_order,
    capture_order as paypal_capture_order,
    verify_webhook,
    compute_subscription_expiry,
)
from app.core.config import settings

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/plans", response_model=list[PlanInfo])
async def list_plans():
    """Return available subscription plans."""
    plans = get_all_plans()
    return [
        PlanInfo(
            id=pid,
            name=p["name"],
            description=p["name"],
            price=p["price"],
            duration_days=p["duration_days"],
            popular=p.get("popular", False),
        )
        for pid, p in plans.items()
    ]


@router.post("/create-order", response_model=CreateOrderResponse)
async def create_order(
    req: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a PayPal order for the given plan."""
    if not get_plan(req.plan_id):
        raise HTTPException(status_code=400, detail="无效的套餐")

    return_url = f"{settings.app_base_url}/payment/success"
    cancel_url = f"{settings.app_base_url}/payment/cancel"

    try:
        result = await paypal_create_order(req.plan_id, return_url, cancel_url)
        order_id = result.get("id", "")
        approval_url = None
        for link in result.get("links", []):
            if link.get("rel") == "approve":
                approval_url = link["href"]
                break
        return CreateOrderResponse(order_id=order_id, approval_url=approval_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建 PayPal 订单失败: {str(e)}")


@router.post("/capture-order", response_model=CaptureOrderResponse)
async def capture_order(
    req: CaptureOrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Capture an approved PayPal order and upgrade user subscription."""
    try:
        result = await paypal_capture_order(req.order_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"捕获 PayPal 订单失败: {str(e)}")

    if result.get("status") != "COMPLETED":
        raise HTTPException(status_code=400, detail="支付未完成")

    # Extract plan type from purchase unit
    purchase_units = result.get("purchase_units", [])
    plan_id = "monthly"
    if purchase_units:
        plan_id = purchase_units[0].get("reference_id", "monthly")

    capture_id = ""
    for unit in purchase_units:
        for cap in unit.get("payments", {}).get("captures", []):
            capture_id = cap.get("id", "")
            break

    amount = 0.0
    if purchase_units:
        amt = purchase_units[0].get("amount", {}).get("value", "0")
        amount = float(amt)

    # Save payment record
    payment = Payment(
        user_id=current_user.id,
        paypal_order_id=req.order_id,
        plan_type=plan_id,
        amount=amount,
        currency="USD",
        status=PaymentStatus.COMPLETED,
    )
    db.add(payment)

    # Upgrade user subscription
    expires_at = compute_subscription_expiry(plan_id)
    # Extend if already premium
    if (
        current_user.subscription_expires_at
        and current_user.subscription_expires_at > datetime.now(timezone.utc)
    ):
        current_user.subscription_expires_at += (
            expires_at - datetime.now(timezone.utc)
        )
    else:
        current_user.subscription_expires_at = expires_at

    current_user.subscription_plan = plan_id
    current_user.role = "premium"
    current_user.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(payment)

    return CaptureOrderResponse(
        status="completed",
        payment_id=str(payment.id),
        subscription_expires_at=current_user.subscription_expires_at,
    )


@router.post("/webhook")
async def paypal_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle PayPal webhook events."""
    body = await request.body()
    headers = dict(request.headers)

    # Verify webhook signature
    verified = await verify_webhook(headers, body)
    if not verified:
        raise HTTPException(status_code=400, detail="Webhook 验证失败")

    import json
    event = json.loads(body) if isinstance(body, bytes) else body
    event_type = event.get("event_type", "")

    if event_type == "CHECKOUT.ORDER.APPROVED":
        order_id = event.get("resource", {}).get("id", "")
        # Order was approved but not yet captured — just log
        pass

    elif event_type == "PAYMENT.CAPTURE.COMPLETED":
        order_id = ""
        resource = event.get("resource", {})
        supplementary = resource.get("supplementary_data", {})
        related_ids = supplementary.get("related_ids", {})
        order_id = related_ids.get("order_id", "")

        if order_id:
            result = await db.execute(
                select(Payment).where(Payment.paypal_order_id == order_id)
            )
            payment = result.scalar_one_or_none()
            if payment and payment.status == PaymentStatus.PENDING:
                payment.status = PaymentStatus.COMPLETED
                await db.commit()

    elif event_type == "PAYMENT.CAPTURE.DENIED":
        resource = event.get("resource", {})
        supplementary = resource.get("supplementary_data", {})
        related_ids = supplementary.get("related_ids", {})
        order_id = related_ids.get("order_id", "")

        if order_id:
            result = await db.execute(
                select(Payment).where(Payment.paypal_order_id == order_id)
            )
            payment = result.scalar_one_or_none()
            if payment:
                payment.status = PaymentStatus.FAILED
                await db.commit()

    elif event_type == "PAYMENT.CAPTURE.REFUNDED":
        resource = event.get("resource", {})
        supplementary = resource.get("supplementary_data", {})
        related_ids = supplementary.get("related_ids", {})
        order_id = related_ids.get("order_id", "")

        if order_id:
            result = await db.execute(
                select(Payment).where(Payment.paypal_order_id == order_id)
            )
            payment = result.scalar_one_or_none()
            if payment:
                payment.status = PaymentStatus.REFUNDED
                await db.commit()

    return {"status": "ok"}


@router.get("/history", response_model=PaymentHistoryResponse)
async def payment_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return payment history for the current user."""
    result = await db.execute(
        select(Payment)
        .where(Payment.user_id == current_user.id)
        .order_by(Payment.created_at.desc())
    )
    payments = result.scalars().all()
    return PaymentHistoryResponse(
        payments=[
            PaymentHistoryItem(
                id=str(p.id),
                plan_type=p.plan_type or "",
                amount=p.amount,
                currency=p.currency,
                status=p.status.value,
                created_at=p.created_at,
            )
            for p in payments
        ]
    )


@router.get("/subscription")
async def subscription_status(
    current_user: User = Depends(get_current_user),
):
    """Return current user's subscription status."""
    is_active = (
        current_user.subscription_expires_at is not None
        and current_user.subscription_expires_at > datetime.now(timezone.utc)
    )
    return {
        "role": current_user.role,
        "plan": current_user.subscription_plan,
        "expires_at": current_user.subscription_expires_at,
        "is_active": is_active,
    }
