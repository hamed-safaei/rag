"""
ماژول تحلیل نتایج بازیابی (child_result) برای تصمیم‌گیری در مورد اینکه
کدام قطعه (child) به‌تنهایی برای پاسخ به سوال کافی است، و در کدام مورد
باید کل والد (parent) بازگردانده شود.

خروجی تابع اصلی analyze_children:
{
    "childs": ["child_title_1", "child_title_2", ...],
    "parents": ["parent_id_1", "parent_id_2", ...]
}
"""

from typing import List, Dict, Any, Literal
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from app.core.config import settings

# ----------------------------
# مدل خروجی ساختاریافته برای هر child
# ----------------------------
class ChildDecision(BaseModel):
    decision: Literal["child", "parent", "none"] = Field(
        description=(
            "child: اگر همین child به تنهایی برای پاسخ به سوال یا بخشی از آن کافی است. "
            "parent: اگر برای پاسخ کامل به سوال، نیاز به کل متن parent است (نه فقط این child). "
            "none: اگر این child (و parent مرتبط با آن) هیچ ربطی به سوال ندارد."
        )
    )
    reason: str = Field(description="دلیل کوتاه تصمیم‌گیری (یک جمله)")


# ----------------------------
# ساخت LLM
# ----------------------------
def get_llm():
    return ChatOpenAI(
        model="gpt-4.1-mini",
        temperature=0,
        max_tokens=256,
        base_url="https://api.gapgpt.app/v1",
        api_key=settings.OPENAI_API_KEY,
    )


SYSTEM_PROMPT = """شما یک دستیار متخصص در تحلیل نتایج بازیابی برای سیستم RAG هستید.
به شما یک «سوال کاربر» و یک «قطعه متن (child)» به همراه «عنوان بخش والد (parent_title)» آن داده می‌شود.

وظیفه شما تصمیم‌گیری بین سه حالت است:

1) "child": اگر محتوای همین قطعه (child_content) به‌تنهایی برای پاسخ به سوال یا حتی بخشی از آن کافی است.
2) "parent": اگر این قطعه مرتبط با سوال است، اما برای پاسخ کامل و دقیق باید کل متن والد (parent) در نظر گرفته شود
   (مثلاً چون قطعه فقط بخشی از یک مفهوم را دارد و ادامه‌ی مطلب در بخش‌های دیگر همان والد است).
3) "none": اگر این قطعه هیچ ارتباطی با سوال ندارد.

فقط و فقط بر اساس متن ارائه‌شده تصمیم بگیرید، نه دانش عمومی خودتان.
پاسخ باید دقیقاً مطابق ساختار خروجی درخواستی باشد."""


USER_TEMPLATE = """سوال کاربر:
{query}

عنوان بخش والد (parent_title): {parent_title}

عنوان قطعه (child_title): {child_title}

محتوای قطعه (child_content):
{child_content}

با توجه به موارد بالا تصمیم بگیرید: child یا parent یا none؟"""


def analyze_children(
    query: str,
    child_result: List[Dict[str, Any]],
    verbose: bool = False,
) -> Dict[str, List[str]]:
    """
    هر یک از childها را یک‌به‌یک بررسی می‌کند و تصمیم می‌گیرد:
      - child_title به لیست childs اضافه شود (کفایت خود قطعه)
      - parent_id به لیست parents اضافه شود (نیاز به کل والد)
      - یا از آن عبور شود (بی‌ربط)

    Args:
        query: پرسش کاربر
        child_result: لیستی از دیکشنری‌ها با کلیدهای
                       parent_id, parent_title, child_title, child_content, rerank_score
        verbose: اگر True باشد، تصمیم و دلیل هر child چاپ می‌شود

    Returns:
        دیکشنری با دو کلید "childs" و "parents"
    """
    llm = get_llm()
    structured_llm = llm.with_structured_output(ChildDecision)

    childs: List[str] = []
    parents: List[str] = []
    seen_parent_ids = set()

    for item in child_result:
        parent_id = item.get("parent_id")
        parent_title = item.get("parent_title", "")
        child_title = item.get("child_title", "")
        child_content = item.get("child_content", "")

        # اگر parent این child قبلاً به دلیل item دیگری به لیست parents اضافه شده،
        # نیازی به بررسی مجدد نیست (چون قرار است کل parent برگردد)
        if parent_id in seen_parent_ids:
            if verbose:
                print(f"[SKIP] child_title='{child_title}' -> parent قبلاً اضافه شده")
            continue

        prompt = USER_TEMPLATE.format(
            query=query,
            parent_title=parent_title,
            child_title=child_title,
            child_content=child_content,
        )

        try:
            result: ChildDecision = structured_llm.invoke(
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ]
            )
        except Exception as e:
            if verbose:
                print(f"[ERROR] child_title='{child_title}' -> {e}")
            continue

        if verbose:
            print(f"[{result.decision.upper()}] child_title='{child_title}' | reason={result.reason}")

        if result.decision == "child":
            if child_title not in childs:
                childs.append(child_title)

        elif result.decision == "parent":
            if parent_id not in seen_parent_ids:
                parents.append(parent_id)
                seen_parent_ids.add(parent_id)

        # decision == "none" -> عبور می‌کنیم، کاری انجام نمی‌شود

    return {"childs": childs, "parents": parents}


# ----------------------------
# نمونه اجرا
# ----------------------------
# if __name__ == "__main__":
#     query = "الگوریتم های جستجو در پایگاه داده برداری چگونه کار میکنند؟"

#     child_result = [
#         {
#             "parent_id": "2",
#             "parent_title": "اجزای اصلی یک سیستم RAG",
#             "child_title": "پایگاه داده برداری (Vector Store)",
#             "child_content": "متن مربوط به الگوریتم‌های HNSW و IVF ...",
#             "rerank_score": 0.3357601761817932,
#         },
#         {
#             "parent_id": "2",
#             "parent_title": "اجزای اصلی یک سیستم RAG",
#             "child_title": "بازیابی و رتبه‌بندی (Retrieval & Reranking)",
#             "child_content": "متن مربوط به بازیابی و رتبه‌بندی مجدد ...",
#             "rerank_score": 0.08122885972261429,
#         },
#         {
#             "parent_id": "6",
#             "parent_title": "پیاده‌سازی عملی با LangChain",
#             "child_title": "پیاده‌سازی عملی با LangChain",
#             "child_content": "متن مربوط به مراحل پیاده‌سازی LangChain ...",
#             "rerank_score": 0.014200640842318535,
#         },
#     ]

#     output = analyze_children(query, child_result, verbose=True)
#     print("\nنتیجه نهایی:")
#     print(output)