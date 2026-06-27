# from dataclasses import dataclass
# from fastembed import SparseTextEmbedding
# from openai import OpenAI
# from qdrant_client import QdrantClient
# from qdrant_client.models import (
#     FusionQuery,
#     NamedSparseVector,
#     NamedVector,
#     Prefetch,
#     SparseVector,
#     Fusion,
# )

# from app.core.config import settings

# # ─────────────────────────────────────────────────────────────────────

# _EMBEDDING_MODEL = "text-embedding-3-large"
# _DENSE_VECTOR_NAME = "dense"
# _SPARSE_VECTOR_NAME = "sparse"

# _openai_client = OpenAI(
#     base_url="https://api.gapgpt.app/v1",
#     api_key=settings.OPENAI_API_KEY,
# )

# _qdrant_client = QdrantClient(url="http://localhost:6333")
# _sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")


# # ────────────────────────────────────────────────────────────────────

# def _embed_dense(text: str) -> list[float]:
#     response = _openai_client.embeddings.create(
#         model=_EMBEDDING_MODEL,
#         input=text,
#     )
#     return response.data[0].embedding


# def _embed_sparse(text: str) -> dict:
#     result = list(_sparse_model.embed([text]))[0]
#     return {
#         "indices": result.indices.tolist(),
#         "values": result.values.tolist(),
#     }


# # ───────────────────────────────────────────────────────────────────

# @dataclass
# class RetrievalResult:
#     score: float
#     child_id: str
#     child_title: str
#     child_content: str
#     parent_id: str
#     parent_title: str
#     parent_content: str


# # ────────────────────────────────────────────────────────────────────

# def search(
#     question: str,
#     collection_name: str = "rag_chunks",
#     top_k: int = 5,
#     prefetch_k: int = 20,
# ) -> list[RetrievalResult]:

#     dense_vector = _embed_dense(question)
#     sparse_vector = _embed_sparse(question)

#     result = _qdrant_client.query_points(
#         collection_name=collection_name,
#         prefetch=[
#             Prefetch(
#                 query=dense_vector,
#                 using=_DENSE_VECTOR_NAME,
#                 limit=prefetch_k,
#             ),
#             Prefetch(
#                 query=SparseVector(**sparse_vector),
#                 using=_SPARSE_VECTOR_NAME,
#                 limit=prefetch_k,
#             ),
#         ],
#         query=FusionQuery(fusion=Fusion.RRF),
#         limit=top_k,
#         with_payload=True,
#     )

#     hits = result.points

#     return [
#         RetrievalResult(
#             score=hit.score,
#             child_id=hit.payload["child_id"],
#             child_title=hit.payload["child_title"],
#             child_content=hit.payload["child_content"],
#             parent_id=hit.payload["parent_id"],
#             parent_title=hit.payload["parent_title"],
#             parent_content=hit.payload["parent_content"],
#         )
#         for hit in hits
#     ]






from dataclasses import dataclass, field
from fastembed import SparseTextEmbedding
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import (
    FusionQuery,
    NamedSparseVector,
    NamedVector,
    Prefetch,
    SparseVector,
    Fusion,
)

from app.core.config import settings

# ── تنظیمات ───────────────────────────────────────────────────────────────────

_EMBEDDING_MODEL = "text-embedding-3-large"
_DENSE_VECTOR_NAME = "dense"
_SPARSE_VECTOR_NAME = "sparse"

_openai_client = OpenAI(
    base_url="https://api.gapgpt.app/v1",
    api_key=settings.OPENAI_API_KEY,
)

_qdrant_client = QdrantClient(url="http://localhost:6333")
_sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")


# ── embedding ──────────────────────────────────────────────────────────────────

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


# ── مدل‌های خروجی ─────────────────────────────────────────────────────────────

@dataclass
class ChildRetrievalResult:
    score: float
    child_id: str
    child_title: str
    child_content: str
    parent_id: str
    parent_title: str
    parent_content: str


@dataclass
class ParentRetrievalResult:
    score: float
    parent_id: str
    parent_title: str
    parent_content: str   # متن کامل — برای ارسال به LLM
    summary: str          # خلاصه‌ای که embed شده
    child_ids: list[str] = field(default_factory=list)


# ── تابع جستجوی پایه (مشترک) ──────────────────────────────────────────────────

def _hybrid_search(
    question: str,
    collection_name: str,
    top_k: int,
    prefetch_k: int,
) -> list:
    """جستجوی hybrid را اجرا کرده و raw hits برمی‌گرداند."""
    dense_vector = _embed_dense(question)
    sparse_vector = _embed_sparse(question)

    result = _qdrant_client.query_points(
        collection_name=collection_name,
        prefetch=[
            Prefetch(
                query=dense_vector,
                using=_DENSE_VECTOR_NAME,
                limit=prefetch_k,
            ),
            Prefetch(
                query=SparseVector(**sparse_vector),
                using=_SPARSE_VECTOR_NAME,
                limit=prefetch_k,
            ),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=top_k,
        with_payload=True,
    )
    return result.points


# ── توابع عمومی ───────────────────────────────────────────────────────────────

def search_children(
    question: str,
    collection_name: str = "rag_chunks",
    top_k: int = 5,
    prefetch_k: int = 20,
) -> list[ChildRetrievalResult]:
    """جستجو در collection مربوط به child chunk ها."""
    hits = _hybrid_search(question, collection_name, top_k, prefetch_k)
    return [
        ChildRetrievalResult(
            score=hit.score,
            child_id=hit.payload["child_id"],
            child_title=hit.payload["child_title"],
            child_content=hit.payload["child_content"],
            parent_id=hit.payload["parent_id"],
            parent_title=hit.payload["parent_title"],
            parent_content=hit.payload["parent_content"],
        )
        for hit in hits
    ]


def search_parents(
    question: str,
    collection_name: str = "rag_parent_chunks",
    top_k: int = 5,
    prefetch_k: int = 20,
) -> list[ParentRetrievalResult]:
    """جستجو در collection مربوط به parent chunk ها (multi-representation indexing)."""
    hits = _hybrid_search(question, collection_name, top_k, prefetch_k)
    return [
        ParentRetrievalResult(
            score=hit.score,
            parent_id=hit.payload["parent_id"],
            parent_title=hit.payload["parent_title"],
            parent_content=hit.payload["parent_content"],
            summary=hit.payload["summary"],
            child_ids=hit.payload.get("child_ids", []),
        )
        for hit in hits
    ]