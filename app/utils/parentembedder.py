import uuid

from fastembed import SparseTextEmbedding
from langchain_openai import ChatOpenAI
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    SparseIndexParams,
    SparseVectorParams,
    VectorParams,
)

from app.core.config import settings
from app.models.Chunks import ParentChunk

# ── تنظیمات ───────────────────────────────────────────────────────────────────

_EMBEDDING_MODEL = "text-embedding-3-large"
_VECTOR_SIZE = 3072
_DENSE_VECTOR_NAME = "dense"
_SPARSE_VECTOR_NAME = "sparse"

_openai_client = OpenAI(
    base_url="https://api.gapgpt.app/v1",
    api_key=settings.OPENAI_API_KEY,
)

_qdrant_client = QdrantClient(url="http://localhost:6333")
_sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")

_llm = ChatOpenAI(
    base_url="https://api.gapgpt.app/v1",
    api_key=settings.OPENAI_API_KEY,
    model="gpt-4o",
    temperature=0,
    streaming=False,
)

_SUMMARIZE_PROMPT = """\
متن زیر یک بخش از یک سند فارسی است.
یک خلاصه فشرده، دقیق و کامل از آن بنویس که:
- همه موضوعات اصلی را پوشش دهد
- اطلاعات کلیدی را حفظ کند
- برای جستجوی معنایی مناسب باشد
- به زبان فارسی باشد

متن:
{content}

خلاصه:"""


# ── توابع کمکی ────────────────────────────────────────────────────────────────

def _summarize(content: str) -> str:
    """محتوای parent را به LLM داده و خلاصه برمی‌گرداند."""
    prompt = _SUMMARIZE_PROMPT.format(content=content)
    response = _llm.invoke(prompt)
    return response.content.strip()


def _embed_dense(text: str) -> list[float]:
    response = _openai_client.embeddings.create(
        model=_EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


def _embed_sparse(text: str) -> dict:
    result = list(_sparse_model.embed([text]))[0]
    return {
        "indices": result.indices.tolist(),
        "values": result.values.tolist(),
    }


# ── collection ─────────────────────────────────────────────────────────────────

def ensure_collection(collection_name: str) -> None:
    existing = {c.name for c in _qdrant_client.get_collections().collections}
    if collection_name not in existing:
        _qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config={
                _DENSE_VECTOR_NAME: VectorParams(
                    size=_VECTOR_SIZE,
                    distance=Distance.COSINE,
                ),
            },
            sparse_vectors_config={
                _SPARSE_VECTOR_NAME: SparseVectorParams(
                    index=SparseIndexParams(on_disk=False),
                ),
            },
        )


# ── upsert ─────────────────────────────────────────────────────────────────────

def summarize_and_store(
    parents: list[ParentChunk],
    collection_name: str = "rag_parent_chunks",
) -> int:
    """
    برای هر parent:
      1. محتوا را به LLM داده و خلاصه تولید می‌کند
      2. خلاصه را dense + sparse embed می‌کند
      3. در Qdrant ذخیره می‌کند

    payload هر نقطه:
    {
        "parent_id":      "2",
        "parent_title":   "عنوان اصلی",
        "parent_content": "متن کامل parent (برای retrieval)",
        "summary":        "خلاصه تولیدشده توسط LLM (چیزی که embed شده)",
        "child_ids":      ["2.1", "2.2", ...],
    }

    Parameters
    ----------
    parents         : خروجی تابع parse_document
    collection_name : نام collection در Qdrant (جدا از collection مربوط به child ها)

    Returns
    -------
    تعداد نقاط upsert‌شده
    """
    ensure_collection(collection_name)

    total_upserted = 0

    for parent in parents:
        if not parent.content:
            continue

        # ── مرحله ۱: تولید خلاصه ─────────────────────────────────────────────
        summary = _summarize(parent.content)

        # ── مرحله ۲: embedding خلاصه ─────────────────────────────────────────
        dense_vector = _embed_dense(summary)
        sparse_vector = _embed_sparse(summary)

        # ── مرحله ۳: ذخیره در Qdrant ─────────────────────────────────────────
        point = PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{collection_name}:{parent.id}")),
            vector={
                _DENSE_VECTOR_NAME: dense_vector,
                _SPARSE_VECTOR_NAME: sparse_vector,
            },
            payload={
                "parent_id": parent.id,
                "parent_title": parent.title,
                "parent_content": parent.content,   # متن کامل — برای context به LLM
                "summary": summary,                  # خلاصه — چیزی که embed شد
                "child_ids": [c.id for c in parent.children],
            },
        )

        _qdrant_client.upsert(collection_name=collection_name, points=[point])
        total_upserted += 1

    return total_upserted