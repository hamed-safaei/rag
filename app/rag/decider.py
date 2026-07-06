#decider.py

import re
from dataclasses import dataclass, field
from app.rag.chians import decider_chain
import json



@dataclass
class DecisionResult:
    parent_ids: list[str] = field(default_factory=list)
    context:    str       = ""     # context نهایی آماده برای LLM اصلی

    @property
    def is_empty(self) -> bool:
        """اگر parent_ids خالی باشد، یعنی Context کافی پیدا نشده (NONE)."""
        return not self.parent_ids


# ─────────────────────────────────────────

def _format_chunks(child_results) -> str:
    """
    parent title :  ...
    child title  :  ...
    child content:
    ...
    parent id    :  X
    """
    parts = []
    for r in child_results:
        parts.append(
            f"parent title :  {r.parent_title}\n"
            f"child title : {r.child_title}\n"
            f"child content :\n{r.child_content}\n"
            f"parent id    :  {r.parent_id}"
        )
    return "\n\n---\n\n".join(parts)


# ───────────────────────────────────────────────────

def _parse_response(raw: str) -> list[str]:
    """
    خروجی JSON مدل را parse می‌کند.
    برمی‌گرداند: parent_ids
    در صورت هرگونه خطا در parse → [] (یعنی معادل NONE)
    """
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not json_match:
        return []

    try:
        data = json.loads(json_match.group())

        parent_ids = data.get("parents", [])

        if not isinstance(parent_ids, list):
            parent_ids = []

        # حذف تکراری‌ها با حفظ ترتیب
        parent_ids = list(dict.fromkeys(str(p) for p in parent_ids))

        return parent_ids

    except (json.JSONDecodeError, AttributeError):
        return []


# ────────────────────────────────────────────────

def _build_context(
    parent_ids: list[str],
    child_results,
) -> str:
    """
    parent_ids خالی → خروجی خالی (NONE)
    در غیر این صورت: برای هر parent_id انتخاب‌شده، کل parent_content
    یک‌بار (به‌صورت یکتا) اضافه می‌شود.
    """
    if not parent_ids:
        return ""

    parts = []
    added_parents = set()
    id_set = set(parent_ids)

    for r in child_results:
        if r.parent_id in id_set and r.parent_id not in added_parents:
            added_parents.add(r.parent_id)
            parts.append(
                f"### [{r.parent_id}] {r.parent_title}\n"
                f"{r.parent_content}"
            )

    return "\n\n".join(parts)


# ─────────────────────────────────────────────────────────

def decide_context(
    query: str,
    child_results,
) -> DecisionResult:
    """
    LangChain chain را صدا می‌زند و بر اساس بررسی تک‌تک Childها (parent_title,
    child_title, child_content)، آرایه‌ی یکتای parent_ids را پر می‌کند و
    context نهایی را می‌سازد.

    پارامترها:
        query        : سؤال کاربر
        child_results: خروجی search_children
    """
    if not child_results:
        return DecisionResult(context="")

    formatted_chunks = _format_chunks(child_results)

    raw_output: str = decider_chain.invoke({
        "query": query,
        "formatted_chunks": formatted_chunks,
    })

    parent_ids = _parse_response(raw_output)
    context = _build_context(parent_ids, child_results)

    return DecisionResult(
        parent_ids=parent_ids,
        context=context,
    )


# ───────────────────────────────────────────────────────────────

def print_decision_result(result: DecisionResult) -> None:
    """نتیجه تصمیم و context انتخاب‌شده را به‌صورت خوانا چاپ می‌کند."""
    print("=" * 60)
    if result.is_empty:
        print("تصمیم      : NONE")
        print("اطلاعات کافی برای پاسخ به این سؤال در منابع یافت نشد.")
        print("=" * 60)
        return
    print(f"Parent IDs : {result.parent_ids}")
    print("=" * 60)
    print("Context نهایی:")
    print("-" * 60)
    print(result.context)
    print("=" * 60)
