"""测试 TTS 服务：音色列表和缓存逻辑"""

import pytest
from app.services.tts_service import TTSService, VOICE_MAP


class TestTTSVoices:
    def test_voice_map_has_chinese_voices(self):
        assert "xiaoxiao" in VOICE_MAP
        assert "yunxi" in VOICE_MAP
        assert len(VOICE_MAP) >= 4

    @pytest.mark.asyncio
    async def test_get_voices(self):
        service = TTSService()
        voices = await service.get_voices()
        assert len(voices) >= 4
        voice_ids = [v["id"] for v in voices]
        assert "xiaoxiao" in voice_ids
        assert "yunxi" in voice_ids

    @pytest.mark.asyncio
    async def test_synthesize_without_key(self):
        """没有配置 API key 时应抛出明确的错误"""
        from app.core.config import settings
        original = settings.azure_tts_key
        settings.azure_tts_key = None
        service = TTSService()
        with pytest.raises(ValueError, match="Azure TTS key not configured"):
            await service.synthesize("你好")
        settings.azure_tts_key = original
