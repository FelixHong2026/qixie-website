"""测试 PayPal 服务：套餐定义和订阅计算"""

from app.services.paypal import get_plan, get_all_plans, compute_subscription_expiry
from datetime import datetime, timezone, timedelta


class TestPlans:
    def test_get_all_plans(self):
        plans = get_all_plans()
        assert "monthly" in plans
        assert "quarterly" in plans
        assert "yearly" in plans
        assert len(plans) == 3

    def test_monthly_plan(self):
        plan = get_plan("monthly")
        assert plan is not None
        assert plan["price"] == 9.99
        assert plan["duration_days"] == 30
        assert plan["name"] == "月卡"

    def test_quarterly_plan(self):
        plan = get_plan("quarterly")
        assert plan is not None
        assert plan["price"] == 24.99
        assert plan["duration_days"] == 90
        assert plan["popular"] is True  # 最受欢迎

    def test_yearly_plan(self):
        plan = get_plan("yearly")
        assert plan is not None
        assert plan["price"] == 89.99
        assert plan["duration_days"] == 365

    def test_unknown_plan(self):
        assert get_plan("nonexistent") is None


class TestSubscriptionExpiry:
    def test_monthly_expiry(self):
        expires = compute_subscription_expiry("monthly")
        now = datetime.now(timezone.utc)
        expected = now + timedelta(days=30)
        # 允许 1 秒偏差
        assert abs((expires - expected).total_seconds()) < 1

    def test_yearly_expiry(self):
        expires = compute_subscription_expiry("yearly")
        now = datetime.now(timezone.utc)
        expected = now + timedelta(days=365)
        assert abs((expires - expected).total_seconds()) < 1

    def test_invalid_plan(self):
        import pytest
        with pytest.raises(ValueError, match="Unknown plan"):
            compute_subscription_expiry("invalid")
