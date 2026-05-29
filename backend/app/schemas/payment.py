from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PlanInfo(BaseModel):
    id: str
    name: str
    description: str
    price: float
    currency: str = "USD"
    duration_days: int
    popular: bool = False


class CreateOrderRequest(BaseModel):
    plan_id: str


class CreateOrderResponse(BaseModel):
    order_id: str
    approval_url: Optional[str] = None


class CaptureOrderRequest(BaseModel):
    order_id: str


class CaptureOrderResponse(BaseModel):
    status: str
    payment_id: str
    subscription_expires_at: datetime


class PaymentHistoryItem(BaseModel):
    id: str
    plan_type: str
    amount: float
    currency: str
    status: str
    created_at: datetime


class PaymentHistoryResponse(BaseModel):
    payments: list[PaymentHistoryItem]
