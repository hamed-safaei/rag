# import json
# from openai import OpenAI
# from app.core.config import settings
# from qdrant_client import QdrantClient


# _qdrant_client = QdrantClient(url="http://localhost:6333")

# client = OpenAI(
#     base_url="https://api.gapgpt.app/v1",
#     api_key=settings.OPENAI_API_KEY,
# )

# SYSTEM_PROMPT = """تو یک ارزیاب دقیق برای یک سیستم RAG هستی.

# به تو یک سؤال کاربر و متن خام قطعات بازیابی‌شده داده می‌شود.
# هر قطعه با خط '---' از بقیه جدا شده و شامل فیلدهای parent id, parent title, child id, child title, child content است.

# برای هر قطعه تصمیم بگیر:

# 1. اگر محتوای همان child به‌تنهایی برای پاسخ به سؤال یا بخشی از آن کافی است، child_id را در آرایه child_ids قرار بده.

# 2. اگر سؤال یا بخشی از آن نیاز به context بزرگ‌تر (کل parent) دارد، فقط parent_id را در آرایه parent_ids قرار بده و child_id مربوط به همان parent را در child_ids نیاور.

# 3. اگر قطعه هیچ ارتباطی با سؤال ندارد، نه parent_id و نه child_id آن را در خروجی نیاور.

# قانون سخت‌گیرانه:
# اگر parent_id یک آیتم در parent_ids قرار گرفت، هیچ‌یک از child_idهای متعلق به همان parent_id نباید در آرایه child_ids قرار بگیرند.
# سپس مقدار retry را تعیین کن:

# - retry = false
# اگر اطلاعات انتخاب‌شده (childها و parentها) برای پاسخ کامل به سؤال کافی هستند و مدل می‌تواند بدون نیاز به بازیابی مجدد پاسخ مناسبی تولید کند.

# - retry = true
# اگر احساس می‌کنی برای پاسخ کامل یا بخشی از سؤال هنوز اطلاعات کافی وجود ندارد، یا احتمال می‌دهی با یک Retrieval دیگر اطلاعات مرتبط بیشتری پیدا شود. حتی اگر بخشی از سؤال قابل پاسخ باشد ولی بخش دیگری نیاز به اطلاعات بیشتری داشته باشد نیز retry باید true باشد.

# فقط خروجی JSON بده، دقیقا با این ساختار و بدون هیچ توضیح اضافه:

# {
#   "parent_ids": ["..."],
#   "child_ids": ["..."],
#   "retry": false Or true
# }
# """

# def evaluate_retrieved_raw_text(question: str, raw_text: str) -> dict:
#     response = client.chat.completions.create(
#         model="gpt-4.1-mini",
#         temperature=0,
#         max_tokens=256,
#         response_format={"type": "json_object"},
#         messages=[
#             {"role": "system", "content": SYSTEM_PROMPT},
#             {"role": "user", "content": f"سؤال کاربر: {question}\n\nقطعات بازیابی‌شده:\n{raw_text}"},
#         ],
#     )
#     return json.loads(response.choices[0].message.content)







# def format_chunks(child_results) -> str:
#     parts = []

#     for r in child_results:
#         if isinstance(r, dict):
#             parent_title = r["parent_title"]
#             child_title = r["child_title"]
#             child_content = r["child_content"]
#             parent_id = r["parent_id"]
#             child_id = r["child_id"]
#         else:
#             # ChildSearchResult یا هر آبجکتی با attributeهای مشابه
#             parent_title = r.parent_title
#             child_title = r.child_title
#             child_content = r.child_content
#             parent_id = r.parent_id
#             child_id = r.child_id

#         parts.append(
#             f"parent title : {parent_title}\n"
#             f"child title : {child_title}\n"
#             f"child content :\n{child_content}\n"
#             f"parent id : {parent_id}\n"
#             f"child id : {child_id}"
#         )

#     return "\n\n---\n\n".join(parts)




# import uuid
# from typing import Any, Dict, List, Optional


# def build_context(
#     ids_input: Dict[str, Any],
#     child_records: List[Dict[str, Any]],
#     parent_collection_name: str = "loader_parents",
#     qdrant_client: Optional[Any] = None,
# ) -> str:

#     parent_ids: List[str] = ids_input.get("parent_ids", []) or []
#     child_ids: List[str] = ids_input.get("child_ids", []) or []

#     client = qdrant_client if qdrant_client is not None else _qdrant_client  # noqa: F821

#     parts: List[str] = []

#     # ------------------------------------------------------------------
#     # ۱) بازیابی والدها (parent_ids) از Qdrant
#     # ------------------------------------------------------------------
#     if parent_ids:
#         # id یکتای نگاشت‌شده در Qdrant که موقع ذخیره‌سازی ساخته بودیم
#         point_ids = [
#             str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{parent_collection_name}:{pid}"))
#             for pid in dict.fromkeys(parent_ids)  # حذف تکراری‌ها با حفظ ترتیب
#         ]

#         records = client.retrieve(
#             collection_name=parent_collection_name,
#             ids=point_ids,
#             with_payload=True,
#             with_vectors=False,
#         )

#         payload_by_parent_id = {
#             rec.payload["parent_id"]: rec.payload for rec in records
#         }

#         for pid in dict.fromkeys(parent_ids):
#             payload = payload_by_parent_id.get(pid)
#             if payload is None:
#                 continue  # پیدا نشد (مثلاً id نامعتبر یا حذف شده)
#             parts.append(
#                 f"### [{payload['parent_id']}] {payload['parent_title']}\n"
#                 f"{payload['parent_content']}"
#             )

#     # ------------------------------------------------------------------
#     # ۲) بازیابی فرزندها (child_ids) از لیست child_records ورودی
#     # ------------------------------------------------------------------
#     if child_ids:
#         # ایندکس کردن رکوردهای فرزند بر اساس child_id برای دسترسی سریع
#         record_by_child_id = {
#             rec["child_id"]: rec for rec in child_records if "child_id" in rec
#         }

#         for cid in dict.fromkeys(child_ids):  # حذف تکراری‌ها با حفظ ترتیب
#             record = record_by_child_id.get(cid)
#             if record is None:
#                 continue  # پیدا نشد
#             parts.append(
#                 f"### [{record['child_id']}] {record['child_title']}\n"
#                 f"{record['child_content']}"
#             )

#     # ------------------------------------------------------------------
#     # ۳) ترکیب نهایی
#     # ------------------------------------------------------------------
#     context_text = "\n\n".join(parts)
#     return context_text