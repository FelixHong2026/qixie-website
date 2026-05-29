"""
Azure TTS (Text-to-Speech) 服务

支持:
- 标准合成：返回音频字节流
- SSML 自定义：语速、音调、风格
- 多音色选择
"""

import hashlib
from typing import Optional
from pathlib import Path

import httpx

from app.core.config import settings


# Azure TTS 音色表
VOICE_MAP = {
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",    # 女声，亲切
    "yunxi": "zh-CN-YunxiNeural",          # 男声，阳光
    "xiaochen": "zh-CN-XiaochenNeural",    # 女声，轻松
    "yunyang": "zh-CN-YunyangNeural",      # 男声，新闻
}


class TTSService:
    """Azure TTS 文本转语音服务"""

    def __init__(self):
        self._tts_key = settings.azure_tts_key
        self._region = settings.azure_tts_region
        self._token_url = f"https://{self._region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
        self._tts_url = f"https://{self._region}.tts.speech.microsoft.com/cognitiveservices/v1"
        self._cache_dir = Path(settings.app_name.replace(" ", "_").lower()) / ".tts_cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, text: str, voice: str, rate: str) -> Path:
        key = hashlib.md5(f"{text}:{voice}:{rate}".encode()).hexdigest()
        return self._cache_dir / f"{key}.mp3"

    async def _get_access_token(self) -> str:
        """获取 Azure TTS 访问令牌"""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self._token_url,
                headers={"Ocp-Apim-Subscription-Key": self._tts_key},
            )
            resp.raise_for_status()
            return resp.text

    async def synthesize(
        self,
        text: str,
        voice: str = "xiaoxiao",
        rate: str = "0%",
        use_cache: bool = True,
    ) -> bytes:
        """
        合成语音。

        Args:
            text: 要合成的文本
            voice: 音色 (xiaoxiao/yunxi/xiaochen/yunyang)
            rate: 语速调整 ("+20%"/"-10%"/"0%")
            use_cache: 是否使用缓存

        Returns:
            MP3 音频字节
        """
        if not self._tts_key:
            raise ValueError("Azure TTS key not configured — set AZURE_TTS_KEY")

        voice_name = VOICE_MAP.get(voice, VOICE_MAP["xiaoxiao"])

        if use_cache:
            cache_path = self._cache_path(text, voice_name, rate)
            if cache_path.exists():
                return cache_path.read_bytes()

        token = await self._get_access_token()

        ssml = f"""<speak version='1.0' xml:lang='zh-CN'>
    <voice name='{voice_name}'>
        <prosody rate='{rate}'>{text}</prosody>
    </voice>
</speak>"""

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self._tts_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/ssml+xml",
                    "X-Microsoft-OutputFormat": "audio-24khz-96kbitrate-mono-mp3",
                    "User-Agent": "QixieChinese",
                },
                content=ssml.encode("utf-8"),
            )
            resp.raise_for_status()
            audio = resp.content

        if use_cache:
            cache_path.write_bytes(audio)

        return audio

    async def get_voices(self) -> list[dict]:
        """列出可用的中文语音"""
        return [
            {"id": "xiaoxiao", "name": "晓晓", "gender": "女", "desc": "亲切自然，适合教学对话"},
            {"id": "yunxi", "name": "云希", "gender": "男", "desc": "阳光活力，适合朗读课文"},
            {"id": "xiaochen", "name": "晓辰", "gender": "女", "desc": "轻松活泼，适合日常对话"},
            {"id": "yunyang", "name": "云扬", "gender": "男", "desc": "新闻播音风格"},
        ]
