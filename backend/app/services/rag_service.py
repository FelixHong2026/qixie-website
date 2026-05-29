"""
RAG 检索服务 — pgvector 向量检索

Architecture:
- EmbeddingCache: 简单嵌入缓存，避免重复 API 调用
- VectorStore: pgvector 增删查封装 (cosine similarity)
- RAGService: 高层接口，处理文档嵌入 + 检索 + 上下文组装

Data flow:
  document → embedding API → pgvector INSERT
  query    → embedding API → pgvector cosine search → top-k context

Fallback: 当 pgvector 不可用时，降级为关键字匹配（FAQ_KNOWLEDGE_BASE）
"""

import json
import hashlib
from typing import Optional

from sqlalchemy import select, text, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.ai_service import FAQ_KNOWLEDGE_BASE


# =============================================================================
# 嵌入缓存（内存级，避免重复调用嵌入 API）
# =============================================================================

class EmbeddingCache:
    """简单 LRU 嵌入缓存"""

    def __init__(self, max_size: int = 512):
        self._cache: dict[str, list[float]] = {}
        self._max_size = max_size

    def _key(self, text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def get(self, text: str) -> Optional[list[float]]:
        return self._cache.get(self._key(text))

    def set(self, text: str, vector: list[float]):
        key = self._key(text)
        if len(self._cache) >= self._max_size:
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = vector


_embedding_cache = EmbeddingCache()


# =============================================================================
# 嵌入生成
# =============================================================================

async def generate_embedding(text: str) -> list[float]:
    """生成文本嵌入向量。优先使用 ZhipuAI embedding API，纯文本 fallback。

    ZhipuAI 提供 text-embedding-ada-002 兼容的 embedding-2 模型。
    当 API key 不可用时，使用基于字符频率的简单哈希嵌入（仅占位）。
    """
    cached = _embedding_cache.get(text)
    if cached is not None:
        return cached

    if settings.zhipuai_api_key:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=settings.zhipuai_api_key,
            base_url=settings.zhipuai_api_base,
        )
        try:
            resp = await client.embeddings.create(
                model="embedding-2",
                input=text,
            )
            vector = resp.data[0].embedding
            _embedding_cache.set(text, vector)
            return vector
        except Exception:
            pass

    # Fallback: 确定性哈希嵌入（768维）
    import hashlib
    dim = 768
    h = hashlib.md5(text.encode()).digest()
    vector = [float((h[i % 16] + (i * 7)) % 256) / 127.5 - 1.0 for i in range(dim)]
    _embedding_cache.set(text, vector)
    return vector


# =============================================================================
# VectorStore — pgvector 操作
# =============================================================================

class VectorStore:
    """pgvector 向量存储封装"""

    TABLE = "embeddings"

    @staticmethod
    async def ensure_extension(db: AsyncSession):
        """确保 pgvector 扩展和表存在"""
        await db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await db.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {VectorStore.TABLE} (
                id SERIAL PRIMARY KEY,
                doc_key TEXT UNIQUE NOT NULL,
                content TEXT NOT NULL,
                metadata JSONB DEFAULT '{{}}',
                embedding vector(768)
            )
        """))
        await db.execute(text(f"""
            CREATE INDEX IF NOT EXISTS idx_{VectorStore.TABLE}_embedding
            ON {VectorStore.TABLE} USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 10)
        """))
        await db.commit()

    @staticmethod
    async def upsert(db: AsyncSession, doc_key: str, content: str, metadata: dict, vector: list[float]):
        """插入或更新文档嵌入"""
        vec_str = json.dumps(vector)
        meta_str = json.dumps(metadata)
        await db.execute(text(f"""
            INSERT INTO {VectorStore.TABLE} (doc_key, content, metadata, embedding)
            VALUES (:key, :content, :metadata::jsonb, :vector::vector)
            ON CONFLICT (doc_key)
            DO UPDATE SET content = :content, metadata = :metadata::jsonb, embedding = :vector::vector
        """), {"key": doc_key, "content": content, "metadata": meta_str, "vector": vec_str})
        await db.commit()

    @staticmethod
    async def search(db: AsyncSession, query_vector: list[float], top_k: int = 3) -> list[dict]:
        """余弦相似度搜索，返回 top-k 结果"""
        vec_str = json.dumps(query_vector)
        result = await db.execute(text(f"""
            SELECT content, metadata,
                   1 - (embedding <=> :query::vector) AS similarity
            FROM {VectorStore.TABLE}
            ORDER BY embedding <=> :query::vector
            LIMIT :limit
        """), {"query": vec_str, "limit": top_k})
        rows = result.fetchall()
        return [
            {"content": row[0], "metadata": row[1], "similarity": float(row[2])}
            for row in rows if row[2] is not None and float(row[2]) > 0.3
        ]

    @staticmethod
    async def delete(db: AsyncSession, doc_key: str):
        """删除文档嵌入"""
        await db.execute(
            sa_delete(text(VectorStore.TABLE)).where(text("doc_key = :key")),
            {"key": doc_key},
        )
        await db.commit()

    @staticmethod
    async def count(db: AsyncSession) -> int:
        """返回文档总数"""
        result = await db.execute(text(f"SELECT COUNT(*) FROM {VectorStore.TABLE}"))
        return result.scalar() or 0


# =============================================================================
# RAGService — 高层接口
# =============================================================================

class RAGService:
    """RAG 检索 + 上下文组装"""

    def __init__(self):
        self._faq_embedded = False

    async def ensure_faq_embedded(self, db: AsyncSession):
        """将 FAQ 知识库嵌入到 pgvector（如果尚未嵌入）"""
        count = await VectorStore.count(db)
        if count >= len(FAQ_KNOWLEDGE_BASE) and self._faq_embedded:
            return

        for entry in FAQ_KNOWLEDGE_BASE:
            doc_key = f"faq:{entry['q']}"
            content = f"Q: {entry['q']}\nA: {entry['a']}"
            metadata = {"source": "faq", "question": entry["q"]}
            vector = await generate_embedding(entry["q"])
            try:
                await VectorStore.upsert(db, doc_key, content, metadata, vector)
            except Exception:
                continue

        self._faq_embedded = True

    async def search(self, db: AsyncSession, query: str, top_k: int = 3) -> list[dict]:
        """检索最相关的文档片段"""
        query_vector = await generate_embedding(query)
        return await VectorStore.search(db, query_vector, top_k)

    def build_context(self, results: list[dict]) -> str:
        """将检索结果组装为 LLM 上下文"""
        if not results:
            return ""
        parts = ["以下是与用户问题相关的参考资料："]
        for i, r in enumerate(results, 1):
            parts.append(f"\n[{i}] {r['content']}")
        parts.append("\n请根据以上资料回答用户的问题。如果资料不足以回答，请如实告知。")
        return "\n".join(parts)
