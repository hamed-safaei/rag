from dataclasses import dataclass
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Fusion,
    FusionQuery,
    Prefetch,
    SparseVector,
)

from app.models.Chunks import ParentChunk
from app.utils.Embedder import (
    _DENSE_VECTOR_NAME,
    _SPARSE_VECTOR_NAME,
    _embed_dense_batch,
    _embed_sparse,
)

_qdrant_client = QdrantClient(url="http://localhost:6333")


# ──────────────────────────────────────────────────

@dataclass
class ChildSearchResult:
    # score: float
    parent_title: str
    child_title: str
    child_content: str
    parent_id: str
    child_id: str
    # parent_content: str


# ─────────────────────────────────────────────────────────────

def search_children(
    query: str,
    collection_name: str = "rag_chunks",
    top_k: int = 5,
) -> list[ChildSearchResult]:
    """
    جستجوی hybrid (dense + sparse / RRF) روی child chunk ها.

    پارامترها:
        query           : متن سؤال کاربر
        collection_name : نام collection در Qdrant
        top_k           : تعداد نتایج بازیابی

    خروجی:
        لیستی از ChildSearchResult مرتب‌شده بر اساس امتیاز
    """
    # ── embedding ──
    dense_vector: list[float] = _embed_dense_batch([query])[0]

    sparse_raw = _embed_sparse(query)         
    sparse_vector = SparseVector(
        indices=sparse_raw["indices"],
        values=sparse_raw["values"],
    )


    
    response = _qdrant_client.query_points(
        collection_name=collection_name,
        prefetch=[
            Prefetch(
                query=dense_vector,
                using=_DENSE_VECTOR_NAME,
                limit=top_k * 2,
            ),
            Prefetch(
                query=sparse_vector,
                using=_SPARSE_VECTOR_NAME,
                limit=top_k * 2,
            ),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=top_k,
        with_payload=True,
    )

    return [
        ChildSearchResult(
            # score=point.score,
            parent_title=point.payload["parent_title"],
            child_title=point.payload["child_title"],
            child_content=point.payload["child_content"],
            parent_id=point.payload["parent_id"],
            child_id=point.payload["child_id"],
            # parent_content=point.payload["parent_content"],
        )
        for point in response.points
    ]


# ───────────────────────────────────────────

# def build_parents_map(parents: list[ParentChunk]) -> dict[str, ParentChunk]:
#     """
#     از لیست ParentChunk ها یک دیکشنری {parent_id -> ParentChunk} می‌سازد.
#     برای دسترسی سریع در لایه تصمیم‌گیری (Decider) استفاده می‌شود.
#     """
#     return {parent.id: parent for parent in parents}