import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { chatApi, paymentApi } from '../api';
import api from '../api/client';
import type { Conversation, Message } from '../api/types';

export default function ChatPage() {
  const { user, logout } = useAuth();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConv, setActiveConv] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [hskLevel, setHskLevel] = useState(1);
  const [chatMode, setChatMode] = useState<'teacher' | 'assistant'>('teacher');
  const [streamingText, setStreamingText] = useState('');
  const [subActive, setSubActive] = useState(false);
  const [subPlan, setSubPlan] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatApi.listConversations().then((res) => setConversations(res.data));
    paymentApi.getSubscription().then((res) => {
      setSubActive(res.data.is_active);
      setSubPlan(res.data.plan);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingText]);

  const loadMessages = async (convId: string) => {
    setActiveConv(convId);
    const res = await chatApi.getMessages(convId);
    setMessages(res.data);
  };

  const newConversation = async () => {
    const res = await chatApi.createConversation({ hsk_level: hskLevel });
    setConversations((prev) => [res.data, ...prev]);
    setActiveConv(res.data.id);
    setMessages([]);
  };

  const sendMessageStream = async (convId: string, text: string, mode: string) => {
    const controller = new AbortController();
    abortRef.current = controller;

    const token = localStorage.getItem('token');
    const baseUrl = api.defaults.baseURL || 'http://localhost:8000/api/v1';

    try {
      const response = await fetch(`${baseUrl}/chat/conversations/${convId}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message: text, mode }),
        signal: controller.signal,
      });

      if (!response.ok || !response.body) {
        throw new Error('Stream request failed');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ') && line !== 'data: [DONE]') {
            const content = line.slice(6);
            fullContent += content;
            setStreamingText(fullContent);
          }
        }
      }

      return fullContent;
    } catch (err) {
      if ((err as Error).name === 'AbortError') return '';
      throw err;
    } finally {
      abortRef.current = null;
      setStreamingText('');
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || !activeConv || sending) return;
    const msg = input;
    setInput('');
    setSending(true);

    const userMsg: Message = {
      id: 'temp-' + Date.now(),
      role: 'user',
      content: msg,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      // 尝试使用 SSE 流式输出
      const fullReply = await sendMessageStream(activeConv, msg, chatMode);

      if (fullReply) {
        const aiMsg: Message = {
          id: 'temp-' + Date.now() + 1,
          role: 'assistant',
          content: fullReply,
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, aiMsg]);
      } else {
        // 降级到非流式
        const res = await chatApi.sendMessage(activeConv, msg, chatMode);
        const aiMsg: Message = {
          id: 'temp-' + Date.now() + 1,
          role: 'assistant',
          content: res.data.reply,
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, aiMsg]);
      }
    } catch {
      const errMsg: Message = {
        id: 'temp-' + Date.now() + 2,
        role: 'assistant',
        content: '抱歉，请求失败，请重试。',
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="h-screen flex flex-col">
      <header className="bg-blue-600 text-white px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold">齐谐中文</h1>
          {subActive ? (
            <span className="text-xs bg-yellow-400 text-yellow-900 px-2 py-0.5 rounded-full font-medium">
              {subPlan === 'yearly' ? '年费' : subPlan === 'quarterly' ? '季费' : '月费'}
            </span>
          ) : (
            <Link to="/plans" className="text-xs bg-yellow-400 text-yellow-900 px-2 py-0.5 rounded-full font-medium hover:bg-yellow-300">
              升级
            </Link>
          )}
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm">{user?.name}</span>
          <button onClick={logout} className="text-sm bg-blue-700 px-3 py-1 rounded hover:bg-blue-800">
            退出
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* 左侧边栏 */}
        <aside className="w-64 bg-gray-50 border-r p-4 flex flex-col gap-3">
          {/* HSK 级别 */}
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium">HSK 级别:</label>
            <select
              value={hskLevel}
              onChange={(e) => setHskLevel(Number(e.target.value))}
              className="text-sm border rounded px-2 py-1"
            >
              {[1, 2, 3, 4, 5, 6].map((l) => (
                <option key={l} value={l}>HSK {l}</option>
              ))}
            </select>
          </div>

          {/* 教师/助教切换 */}
          <div className="flex rounded-lg border overflow-hidden">
            <button
              onClick={() => setChatMode('teacher')}
              className={`flex-1 py-2 text-sm font-medium ${
                chatMode === 'teacher'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
            >
              👨‍🏫 教师
            </button>
            <button
              onClick={() => setChatMode('assistant')}
              className={`flex-1 py-2 text-sm font-medium ${
                chatMode === 'assistant'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
            >
              💬 助教
            </button>
          </div>

          <button
            onClick={newConversation}
            className="w-full py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
          >
            + 新对话
          </button>
          <div className="flex-1 overflow-y-auto space-y-2">
            {conversations.map((conv) => (
              <button
                key={conv.id}
                onClick={() => loadMessages(conv.id)}
                className={`w-full text-left p-2 rounded text-sm ${
                  activeConv === conv.id ? 'bg-blue-100 text-blue-800' : 'hover:bg-gray-200'
                }`}
              >
                <div className="truncate font-medium">{conv.title}</div>
                <div className="text-xs text-gray-400">HSK {conv.hsk_level}</div>
              </button>
            ))}
          </div>
        </aside>

        {/* 主聊天区 */}
        <main className="flex-1 flex flex-col">
          {/* 模式提示 */}
          {activeConv && (
            <div className="px-6 py-2 bg-blue-50 border-b text-sm text-blue-700">
              {chatMode === 'teacher'
                ? '👨‍🏫 当前为 AI 教师模式 — 齐老师将按照教学流程授课'
                : '💬 当前为 AI 助教模式 — 小齐将回答你的中文学习问题'}
            </div>
          )}

          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {!activeConv && (
              <div className="text-center text-gray-400 mt-20">
                <p className="text-lg">欢迎来到齐谐中文</p>
                <p className="mt-2">选择左侧对话或创建新对话开始学习</p>
                <p className="mt-1 text-sm">左侧可切换 AI 教师授课 / AI 助教答疑模式</p>
              </div>
            )}
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[70%] p-3 rounded-lg whitespace-pre-wrap ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : msg.role === 'system'
                      ? 'bg-gray-100 text-gray-500 italic'
                      : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}
            {sending && streamingText && (
              <div className="flex justify-start">
                <div className="max-w-[70%] p-3 rounded-lg bg-gray-100 text-gray-900 whitespace-pre-wrap">
                  {streamingText}
                  <span className="animate-pulse">▌</span>
                </div>
              </div>
            )}
            {sending && !streamingText && (
              <div className="flex justify-start">
                <div className="bg-gray-100 p-3 rounded-lg text-gray-400">
                  <span className="animate-pulse">正在输入...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="border-t p-4">
            <div className="flex gap-2 max-w-4xl mx-auto w-full">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                placeholder={chatMode === 'teacher' ? '输入你的回答...' : "输入你的中文学习问题..."}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                disabled={!activeConv || sending}
              />
              <button
                onClick={sendMessage}
                disabled={!activeConv || sending || !input.trim()}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                发送
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
