from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.user import User, Conversation, Message, MessageRole
from app.schemas.user import (
    ConversationCreate, ConversationResponse, MessageResponse, ChatRequest, ChatResponse,
)
from app.api.v1.deps import get_current_user
from app.services.ai_service import AIService

router = APIRouter(prefix="/chat", tags=["AI 对话"])


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
    )
    return result.scalars().all()


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    body: ConversationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv = Conversation(user_id=user.id, title=body.title, hsk_level=body.hsk_level)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


@router.get("/conversations/{conv_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    conv_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(Conversation.id == conv_id, Conversation.user_id == user.id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")

    msgs = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.created_at)
    )
    return msgs.scalars().all()


@router.post("/conversations/{conv_id}/chat", response_model=ChatResponse)
async def chat(
    conv_id: str,
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(Conversation.id == conv_id, Conversation.user_id == user.id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")

    # 保存用户消息
    user_msg = Message(conversation_id=conv.id, role=MessageRole.USER, content=body.message)
    db.add(user_msg)
    await db.commit()

    # 获取历史消息
    history_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at)
    )
    history = history_result.scalars().all()

    # 调用 AI（支持教师/助教模式）
    ai_service = AIService()
    mode = body.mode or "teacher"
    reply = await ai_service.chat(history, hsk_level=conv.hsk_level, mode=mode)

    # 保存 AI 回复
    assistant_msg = Message(conversation_id=conv.id, role=MessageRole.ASSISTANT, content=reply)
    db.add(assistant_msg)
    await db.commit()

    return ChatResponse(reply=reply)


@router.post("/conversations/{conv_id}/chat/stream")
async def chat_stream(
    conv_id: str,
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SSE 流式对话端点 — 提供打字机效果"""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conv_id, Conversation.user_id == user.id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")

    # 保存用户消息
    user_msg = Message(conversation_id=conv.id, role=MessageRole.USER, content=body.message)
    db.add(user_msg)
    await db.commit()

    # 获取历史消息
    history_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at)
    )
    history = history_result.scalars().all()

    ai_service = AIService()
    mode = body.mode or "teacher"

    async def generate():
        full_reply = ""
        async for chunk in ai_service.chat_stream(history, hsk_level=conv.hsk_level, mode=mode):
            full_reply += chunk
            yield f"data: {chunk}\n\n"
        # 保存完整回复到数据库
        assistant_msg = Message(conversation_id=conv.id, role=MessageRole.ASSISTANT, content=full_reply)
        async with db.begin():
            db.add(assistant_msg)
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
