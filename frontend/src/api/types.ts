export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  hsk_level: number;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
}

export interface ChatResponse {
  reply: string;
}

export interface ChatRequest {
  message: string;
  mode?: 'teacher' | 'assistant';
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface PlanInfo {
  id: string;
  name: string;
  description: string;
  price: number;
  currency: string;
  duration_days: number;
  popular: boolean;
}

export interface CreateOrderResponse {
  order_id: string;
  approval_url: string | null;
}

export interface CaptureOrderResponse {
  status: string;
  payment_id: string;
  subscription_expires_at: string;
}

export interface SubscriptionStatus {
  role: string;
  plan: string | null;
  expires_at: string | null;
  is_active: boolean;
}
