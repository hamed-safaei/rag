import uuid

from fastembed import SparseTextEmbedding
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
from app.models.Chunks import ChildChunk, ParentChunk

# ─────────────────────────────────────────────────────────────────────

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


# ────────────────────────────────────────────────────────────────────

def _embed_dense_batch(texts: list[str]) -> list[list[float]]:
    response = _openai_client.embeddings.create(
        model=_EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]


def _embed_sparse(text: str) -> dict:
    result = list(_sparse_model.embed([text]))[0]
    return {
        "indices": result.indices.tolist(),
        "values": result.values.tolist(),
    }


# ───────────────────────────────────────────────────────────────────

def ensure_collection(collection_name: str) -> None:
    """
    Collection را با دو named vector می‌سازد:
      - dense  : بردار float برای semantic search
      - sparse : بردار BM25 برای keyword search
    """
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


# ───────────────────────────────────────────────────────────────────────

def embed_and_store(
    parents: list[ParentChunk],
    collection_name: str = "rag_chunks",
    batch_size: int = 32,
) -> int:
    """
    child chunk ها را با دو بردار dense + sparse embed کرده و در Qdrant ذخیره می‌کند.
    """
    ensure_collection(collection_name)

    pairs: list[tuple[ChildChunk, ParentChunk]] = [
        (child, parent)
        for parent in parents
        for child in parent.children
    ]

    if not pairs:
        return 0

    total_upserted = 0

    for batch_start in range(0, len(pairs), batch_size):
        batch = pairs[batch_start : batch_start + batch_size]
        texts = [
            f"{child.title}\n{child.content}"
            for child, _ in batch
        ]
        dense_vectors = _embed_dense_batch(texts)

        points: list[PointStruct] = []
        for (child, parent), dense_vector, text in zip(batch, dense_vectors, texts):
            sparse_vector = _embed_sparse(text)

            points.append(
                PointStruct(
                    id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{collection_name}:{child.id}")),
                    vector={
                        _DENSE_VECTOR_NAME: dense_vector,
                        _SPARSE_VECTOR_NAME: sparse_vector,
                    },
                    payload={
                        "child_id": child.id,
                        "child_title": child.title,
                        "child_content": child.content,
                        "parent_id": parent.id,
                        "parent_title": parent.title,
                        "parent_content": parent.content,
                    },
                )
            )

        _qdrant_client.upsert(collection_name=collection_name, points=points)
        total_upserted += len(points)

    return total_upserted