from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.api.v1.deps import get_current_user
from app.models.user import User
from app.services.tts_service import TTSService

router = APIRouter(prefix="/tts", tags=["语音合成"])
tts_service = TTSService()


@router.get("/voices")
async def list_voices():
    """列出可用音色"""
    return await tts_service.get_voices()


@router.get("/synthesize")
async def synthesize(
    text: str = Query(..., description="要合成的文本"),
    voice: str = Query("xiaoxiao", description="音色"),
    rate: str = Query("0%", description="语速调整"),
    user: User = Depends(get_current_user),
):
    """文本转语音 — 返回 MP3 音频"""
    if not text.strip():
        raise HTTPException(status_code=400, detail="文本不能为空")

    try:
        audio = await tts_service.synthesize(text, voice=voice, rate=rate)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"语音合成失败: {str(e)}")

    return Response(content=audio, media_type="audio/mpeg")
