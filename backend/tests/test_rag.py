"""测试 RAG 服务：嵌入缓存和向量存储查询构建"""

import pytest
from app.services.rag_service import EmbeddingCache, generate_embedding


class TestEmbeddingCache:
    def test_set_and_get(self):
        cache = EmbeddingCache(max_size=10)
        cache.set("hello", [0.1, 0.2, 0.3])
        result = cache.get("hello")
        assert result == [0.1, 0.2, 0.3]

    def test_cache_miss(self):
        cache = EmbeddingCache()
        assert cache.get("nonexistent") is None

    def test_cache_eviction(self):
        cache = EmbeddingCache(max_size=2)
        cache.set("a", [1.0])
        cache.set("b", [2.0])
        cache.set("c", [3.0])  # should evict "a"
        assert cache.get("a") is None
        assert cache.get("b") == [2.0]
        assert cache.get("c") == [3.0]


class TestEmbeddingGeneration:
    @pytest.mark.asyncio
    async def test_fallback_embedding(self):
        """当没有 API key 时，应生成确定性嵌入"""
        from app.core.config import settings
        original_key = settings.zhipuai_api_key
        settings.zhipuai_api_key = None

        vec = await generate_embedding("测试文本")
        assert len(vec) == 768
        # 确定性：相同输入应产生相同输出
        vec2 = await generate_embedding("测试文本")
        assert vec == vec2

        # 不同输入应产生不同嵌入
        vec3 = await generate_embedding("不同文本")
        assert vec != vec3

        settings.zhipuai_api_key = original_key

    @pytest.mark.asyncio
    async def test_embedding_cache_used(self):
        """重复调用应使用缓存"""
        from app.core.config import settings
        original_key = settings.zhipuai_api_key
        settings.zhipuai_api_key = None

        vec1 = await generate_embedding("缓存测试")
        vec2 = await generate_embedding("缓存测试")
        assert vec1 == vec2  # 缓存命中

        settings.zhipuai_api_key = original_key
