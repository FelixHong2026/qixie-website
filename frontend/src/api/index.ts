import api from './client';
import type { AuthResponse, Conversation, Message, ChatResponse, PlanInfo, CreateOrderResponse, CaptureOrderResponse, SubscriptionStatus } from './types';

export const authApi = {
  register: (data: { email: string; password: string; name: string }) =>
    api.post<AuthResponse>('/auth/register', data),

  login: (data: { email: string; password: string }) =>
    api.post<AuthResponse>('/auth/login', data),

  getMe: () => api.get<AuthResponse['user']>('/auth/me'),
};

export const chatApi = {
  listConversations: () =>
    api.get<Conversation[]>('/chat/conversations'),

  createConversation: (data: { title?: string; hsk_level?: number }) =>
    api.post<Conversation>('/chat/conversations', data),

  getMessages: (convId: string) =>
    api.get<Message[]>(`/chat/conversations/${convId}/messages`),

  sendMessage: (convId: string, message: string, mode: string = 'teacher') =>
    api.post<ChatResponse>(`/chat/conversations/${convId}/chat`, { message, mode }),

  getStreamUrl: (convId: string) =>
    `${api.defaults.baseURL}/chat/conversations/${convId}/chat/stream`,
};

export const paymentApi = {
  getPlans: () => api.get<PlanInfo[]>('/payments/plans'),

  createOrder: (planId: string) =>
    api.post<CreateOrderResponse>('/payments/create-order', { plan_id: planId }),

  captureOrder: (orderId: string) =>
    api.post<CaptureOrderResponse>('/payments/capture-order', { order_id: orderId }),

  getSubscription: () => api.get<SubscriptionStatus>('/payments/subscription'),
};
