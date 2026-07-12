
import uuid
from typing import Any, Dict, List, Optional
from qdrant_client import QdrantClient

_qdrant_client = QdrantClient(url="http://localhost:6333")

def build_context(
    ids_input: Dict[str, Any],
    child_records: List[Dict[str, Any]],
    parent_collection_name: str = "loader_parents",
    qdrant_client: Optional[Any] = None,
) -> str:

    parent_ids: List[str] = ids_input.get("parent_ids", []) or []
    child_ids: List[str] = ids_input.get("child_ids", []) or []

    client = qdrant_client if qdrant_client is not None else _qdrant_client  # noqa: F821

    parts: List[str] = []

    # ------------------------------------------------------------------
    # ۱) بازیابی والدها (parent_ids) از Qdrant
    # ------------------------------------------------------------------
    if parent_ids:
        # id یکتای نگاشت‌شده در Qdrant که موقع ذخیره‌سازی ساخته بودیم
        point_ids = [
            str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{parent_collection_name}:{pid}"))
            for pid in dict.fromkeys(parent_ids)  # حذف تکراری‌ها با حفظ ترتیب
        ]

        records = client.retrieve(
            collection_name=parent_collection_name,
            ids=point_ids,
            with_payload=True,
            with_vectors=False,
        )

        payload_by_parent_id = {
            rec.payload["parent_id"]: rec.payload for rec in records
        }

        for pid in dict.fromkeys(parent_ids):
            payload = payload_by_parent_id.get(pid)
            if payload is None:
                continue  # پیدا نشد (مثلاً id نامعتبر یا حذف شده)
            parts.append(
                f"### [{payload['parent_id']}] {payload['parent_title']}\n"
                f"{payload['parent_content']}"
            )

    # ------------------------------------------------------------------
    # ۲) بازیابی فرزندها (child_ids) از لیست child_records ورودی
    # ------------------------------------------------------------------
    if child_ids:
        # ایندکس کردن رکوردهای فرزند بر اساس child_id برای دسترسی سریع
        record_by_child_id = {
            rec["child_id"]: rec for rec in child_records if "child_id" in rec
        }

        for cid in dict.fromkeys(child_ids):  # حذف تکراری‌ها با حفظ ترتیب
            record = record_by_child_id.get(cid)
            if record is None:
                continue  # پیدا نشد
            parts.append(
                f"### [{record['child_id']}] {record['child_title']}\n"
                f"{record['child_content']}"
            )

    # ------------------------------------------------------------------
    # ۳) ترکیب نهایی
    # ------------------------------------------------------------------
    context_text = "\n\n".join(parts)
    return context_text