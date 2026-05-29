"""测试 AI 服务：消息构建、FAQ 检索、API 调用"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.user import Message, MessageRole
from app.services.ai_service import AIService, FAQ_KNOWLEDGE_BASE


@pytest.fixture
def ai_service():
    return AIService()


class TestFAQLookup:
    def test_exact_match(self, ai_service):
        """FAQ 知识库能匹配到已知问题"""
        answer = ai_service._lookup_faq("HSK是什么")
        assert answer is not None
        assert "HSK" in answer

    def test_partial_match(self, ai_service):
        """部分匹配也能返回 FAQ"""
        answer = ai_service._lookup_faq("讲一下HSK是什么？")
        assert answer is not None
        assert "HSK" in answer

    def test_fuzzy_match(self, ai_service):
        """中文模糊匹配（字符重叠 > 50%）"""
        answer = ai_service._lookup_faq("我想知道怎么记住汉字，有什么好方法吗")
        assert answer is not None
        assert "汉字" in answer

    def test_no_match(self, ai_service):
        """不匹配的问题返回 None"""
        answer = ai_service._lookup_faq("今天天气真好")
        assert answer is None

    def test_faq_count(self):
        """FAQ 知识库应有至少 15 条记录"""
        assert len(FAQ_KNOWLEDGE_BASE) >= 15


class TestBuildMessages:
    def test_teacher_mode(self, ai_service):
        history = [
            Message(id="1", conversation_id="c1", role=MessageRole.USER, content="你好", created_at=None),
        ]
        messages = ai_service._build_messages(history, hsk_level=1.0, mode="teacher")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "你好"
        assert "HSK1" in messages[0]["content"]

    def test_assistant_mode(self, ai_service):
        history = [
            Message(id="2", conversation_id="c1", role=MessageRole.USER, content="怎么记住汉字", created_at=None),
        ]
        messages = ai_service._build_messages(history, hsk_level=2.0, mode="assistant")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "小齐" in messages[0]["content"]

    def test_empty_history(self, ai_service):
        messages = ai_service._build_messages([], hsk_level=1.0, mode="teacher")
        assert len(messages) == 1
        assert messages[0]["role"] == "system"


class TestAIServiceChat:
    @pytest.mark.asyncio
    async def test_assistant_mode_uses_faq(self, ai_service):
        """助教模式应优先使用 FAQ 而非调用 API"""
        history = [
            Message(id="3", conversation_id="c1", role=MessageRole.USER, content="HSK是什么", created_at=None),
        ]
        with patch.object(ai_service, "_get_client") as mock_get_client:
            reply = await ai_service.chat(history, hsk_level=1.0, mode="assistant")
            mock_get_client.assert_not_called()
            assert reply is not None
            assert "HSK" in reply

    @pytest.mark.asyncio
    async def test_teacher_mode_calls_api(self, ai_service):
        """教师模式应调用 API"""
        history = [
            Message(id="4", conversation_id="c1", role=MessageRole.USER, content="你好", created_at=None),
        ]
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "你好！我是齐老师。今天我们来学习中文。"
        mock_create = AsyncMock(return_value=mock_response)

        mock_client = MagicMock()
        mock_client.chat.completions.create = mock_create

        with patch.object(ai_service, "_get_client", return_value=mock_client):
            reply = await ai_service.chat(history, hsk_level=1.0, mode="teacher")
            assert reply == "你好！我是齐老师。今天我们来学习中文。"
            mock_create.assert_called_once()
