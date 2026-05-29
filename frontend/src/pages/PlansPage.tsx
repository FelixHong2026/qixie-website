import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { paymentApi } from '../api';
import type { PlanInfo } from '../api/types';

declare global {
  interface Window {
    paypal?: any;
  }
}

function loadPayPalSDK(): Promise<void> {
  return new Promise((resolve) => {
    if (window.paypal) return resolve();
    const script = document.createElement('script');
    script.src = `https://www.paypal.com/sdk/js?client-id=${import.meta.env.VITE_PAYPAL_CLIENT_ID || 'test'}&currency=USD`;
    script.async = true;
    script.onload = () => resolve();
    document.body.appendChild(script);
  });
}

export default function PlansPage() {
  const [plans, setPlans] = useState<PlanInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    paymentApi.getPlans()
      .then((res) => setPlans(res.data))
      .catch(() => setError('无法加载套餐信息'))
      .finally(() => setLoading(false));
  }, []);

  const renderPayPalButton = useCallback(async (planId: string) => {
    setProcessing(true);
    setError('');
    try {
      await loadPayPalSDK();
      const res = await paymentApi.createOrder(planId);
      const { order_id } = res.data;

      if (window.paypal) {
        const container = document.getElementById('paypal-button-container');
        if (!container) return;

        container.innerHTML = '';
        window.paypal.Buttons({
          createOrder: () => order_id,
          onApprove: async (data: any) => {
            try {
              const captureRes = await paymentApi.captureOrder(data.orderID);
              if (captureRes.data.status === 'completed') {
                navigate('/payment/success');
              }
            } catch {
              navigate('/payment/failed');
            }
          },
          onCancel: () => {
            setSelectedPlan(null);
            setProcessing(false);
          },
          onError: () => {
            setError('PayPal 加载失败，请重试');
            setProcessing(false);
          },
        }).render('#paypal-button-container');
      }
    } catch {
      setError('创建订单失败，请重试');
      setProcessing(false);
    }
  }, [navigate]);

  const handleSelectPlan = async (planId: string) => {
    setSelectedPlan(planId);
    await renderPayPalButton(planId);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-gray-500">加载中...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-indigo-50 to-white">
      <div className="max-w-5xl mx-auto px-4 py-20">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">选择你的学习计划</h1>
          <p className="text-lg text-gray-600">解锁全部 AI 教师功能，加速中文学习之旅</p>
        </div>

        {error && (
          <div className="max-w-md mx-auto mb-6 p-3 bg-red-50 text-red-600 rounded-lg text-center text-sm">
            {error}
          </div>
        )}

        <div className="grid md:grid-cols-3 gap-8 mb-12">
          {plans.map((plan) => (
            <div
              key={plan.id}
              className={`relative bg-white rounded-2xl shadow-sm border-2 transition-all duration-200 ${
                selectedPlan === plan.id
                  ? 'border-indigo-500 shadow-lg scale-105'
                  : plan.popular
                  ? 'border-indigo-400 shadow-md'
                  : 'border-gray-100 hover:border-indigo-200'
              }`}
            >
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-indigo-600 text-white text-xs font-semibold px-4 py-1 rounded-full">
                  最受欢迎
                </div>
              )}
              <div className="p-8">
                <h3 className="text-xl font-semibold text-gray-900 mb-2">{plan.name}</h3>
                <div className="mb-6">
                  <span className="text-4xl font-bold text-gray-900">${plan.price}</span>
                  <span className="text-gray-500 ml-1">USD</span>
                </div>
                <ul className="space-y-3 mb-8 text-sm text-gray-600">
                  <li className="flex items-center gap-2">
                    <span className="text-indigo-500">✓</span>
                    AI 教师无限对话
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-indigo-500">✓</span>
                    个性化学习路径
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-indigo-500">✓</span>
                    发音评估与纠错
                  </li>
                  {plan.id !== 'monthly' && (
                    <li className="flex items-center gap-2">
                      <span className="text-indigo-500">✓</span>
                      优先使用最新功能
                    </li>
                  )}
                </ul>
                <button
                  onClick={() => handleSelectPlan(plan.id)}
                  disabled={processing && selectedPlan === plan.id}
                  className={`w-full py-3 rounded-xl font-semibold text-sm transition-all ${
                    selectedPlan === plan.id
                      ? 'bg-indigo-600 text-white cursor-default'
                      : 'bg-indigo-600 text-white hover:bg-indigo-700 active:scale-[0.98]'
                  } disabled:opacity-50`}
                >
                  {processing && selectedPlan === plan.id ? '处理中...' : '选择此计划'}
                </button>
              </div>
            </div>
          ))}
        </div>

        {selectedPlan && (
          <div className="max-w-md mx-auto">
            <div id="paypal-button-container" className="min-h-[40px]" />
            <p className="text-center text-xs text-gray-400 mt-3">
              支付即表示同意服务条款。支付由 PayPal 安全处理。
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
