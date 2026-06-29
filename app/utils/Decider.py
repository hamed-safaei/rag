"""
Decider.py
──────────
لایه تصمیم‌گیری Context برای سیستم RAG.

سه حالت تصمیم:
  CHILD  → فقط child های بازیابی‌شده کافی‌اند
  PARENT → یک یا چند parent کامل نیاز است
  MIXED  → بعضی parent ها کامل + بعضی فقط child مشخص
"""

import json
import re
from dataclasses import dataclass, field

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import settings


# ──────────────────────────── LLM ────────────────────────────────────

_llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    max_tokens=256,
    base_url="https://api.gapgpt.app/v1",
    api_key=settings.OPENAI_API_KEY,
)


# ─────────────────────────── پرامپت ─────────────────────────────────

_SYSTEM_PROMPT = """\
تو یک دستیار هوشمند هستی که وظیفه‌ات تصمیم‌گیری درباره میزان Context موردنیاز \
برای پاسخ‌گویی به سؤال کاربر است.

ورودی:
1. سؤال کاربر
2. مجموعه‌ای از Child chunk های بازیابی‌شده از Vector Store
   هر Child دارای این فیلدها است: child_title، child_content، parent_title، parent_id، child_id

وظیفه تو پاسخ دادن به سؤال نیست؛ فقط باید مشخص کنی چه Context ای لازم است.

━━━ سه حالت ممکن ━━━

① CHILD — همان Child های بازیابی‌شده برای پاسخ کامل کافی‌اند:
{{"decision": "CHILD", "child_ids": ["3.1", "6.2"]}}

② PARENT — یک یا چند Parent باید کامل خوانده شوند:
{{"decision": "PARENT", "parent_ids": ["3", "6"]}}

③ MIXED — بعضی Parent ها کامل لازم‌اند و بعضی فقط یک Child مشخص کافی است:
{{"decision": "MIXED", "parent_ids": ["3"], "child_ids": ["6.1"]}}

━━━ راهنمای استفاده از parent_title ━━━

هر Child یک فیلد «parent_title» دارد که عنوان کلی بخشی است که این Child در آن قرار دارد.
از این فیلد به‌عنوان سیگنال اصلی برای تشخیص نیاز به Parent کامل استفاده کن:

• اگر سؤال یک مفهوم جزئی و مشخص را می‌پرسد و Child بازیابی‌شده دقیقاً همان را پوشش می‌دهد،
  نیازی به Parent کامل نیست — حتی اگر parent_title یک موضوع بزرگ‌تر باشد.
  مثال: سؤال «مشکل کمبود داده‌های آموزشی فارسی چیست؟»
         → Child 3.3 با parent_title «چالش‌های RAG برای زبان فارسی» کافی است (CHILD)

• اگر سؤال کلی یا ساختاری است و parent_title نشان می‌دهد Child های دیگری در همان Parent
  وجود دارند که احتمالاً بازیابی نشده‌اند، Parent کامل لازم است.
  مثال: سؤال «چالش‌های RAG برای زبان فارسی را کامل توضیح بده»
         → parent_title «چالش‌های RAG برای زبان فارسی» مطابق سؤال است → PARENT

• اگر Child های بازیابی‌شده از Parent های مختلف با parent_title های متفاوت‌اند
  و سؤال دقیقاً همان موضوع‌های جداگانه را می‌پرسد، هر Child به‌تنهایی کافی است.
  مثال: سؤال «تقسیم‌بندی متن و کمبود داده فارسی را توضیح بده»
         → Child 2.2 (parent: «اجزای RAG») + Child 3.3 (parent: «چالش‌های فارسی») → CHILD

━━━ قوانین تصمیم‌گیری ━━━

• CHILD انتخاب کن اگر:
  - سؤال درباره مفهوم یا بخش‌های مشخصی است
  - Child های بازیابی‌شده اطلاعات کافی برای پاسخ کامل دارند
  - parent_title ها نشان می‌دهند Child های بازیابی‌شده دقیقاً موضوع سؤال را پوشش می‌دهند

• PARENT انتخاب کن اگر:
  - سؤال کلی، ساختاری، یا درباره مرور کامل یک موضوع است
  - parent_title با موضوع کلی سؤال مطابقت دارد و احتمال دارد Child های دیگری بازیابی نشده باشند

• MIXED انتخاب کن اگر:
  - برای بعضی Parent ها سؤال جزئی است و Child کافی است (parent_title فقط پس‌زمینه است)
  - برای بعضی Parent های دیگر سؤال کلی است و Parent کامل لازم است (parent_title با سؤال مطابق است)

نکات مهم:
* فرض نکن تمام Child های یک Parent بازیابی شده‌اند
* در MIXED فقط parent_id هایی را بنویس که کامل لازم‌اند؛ بقیه در child_ids
* هیچ توضیح اضافه‌ای ننویس — فقط JSON خالص برگردان
"""

_HUMAN_TEMPLATE = """\
سؤال کاربر:
{query}

Child های بازیابی‌شده:
{formatted_chunks}
"""

_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM_PROMPT),
    ("human", _HUMAN_TEMPLATE),
])

_chain = _prompt | _llm | StrOutputParser()


# ───────────────────────── مدل خروجی ────────────────────────────────

@dataclass
class DecisionResult:
    decision: str                  # "CHILD" | "PARENT" | "MIXED"
    parent_ids: list[str] = field(default_factory=list)
    child_ids: list[str]  = field(default_factory=list)
    context: str          = ""     # context نهایی آماده برای LLM اصلی


# ───────────────────── فرمت‌بندی chunks برای LLM ────────────────────

def _format_chunks(child_results) -> str:
    """
    [score] child_title
    child_content
    parent title :  ...
    parent id    :  X
    child id     :  X.Y
    """
    parts = []
    for r in child_results:
        parts.append(
            f"[{r.score:.3f}] {r.child_title}\n"
            f"{r.child_content}\n"
            f"parent title :  {r.parent_title}\n"
            f"parent id    :  {r.parent_id}\n"
            f"child id     :  {r.child_id}"
        )
    return "\n\n---\n\n".join(parts)


# ──────────────────────── parse خروجی LLM ───────────────────────────

def _parse_response(raw: str) -> tuple[str, list[str], list[str]]:
    """
    خروجی JSON مدل را parse می‌کند.
    برمی‌گرداند: (decision, parent_ids, child_ids)
    در صورت خطا → ("PARENT", [], [])
    """
    json_match = re.search(r"\{.*?\}", raw, re.DOTALL)
    if not json_match:
        return "PARENT", [], []

    try:
        data = json.loads(json_match.group())
        decision = data.get("decision", "PARENT").upper()

        if decision not in ("CHILD", "PARENT", "MIXED"):
            decision = "PARENT"

        parent_ids = data.get("parent_ids", [])
        child_ids  = data.get("child_ids",  [])

        # سازگاری با فرمت قدیمی: {"ids": [...]}
        if not parent_ids and not child_ids:
            legacy_ids = data.get("ids", [])
            if decision == "PARENT":
                parent_ids = legacy_ids
            else:
                child_ids = legacy_ids

        return decision, parent_ids, child_ids

    except (json.JSONDecodeError, AttributeError):
        return "PARENT", [], []


# ─────────────────────── ساخت context نهایی ─────────────────────────

def _build_context(
    decision: str,
    parent_ids: list[str],
    child_ids: list[str],
    child_results,
    parents_map: dict,
) -> str:
    """
    بر اساس تصمیم LLM، context نهایی را می‌سازد.

    CHILD  → child_content فقط child_ids انتخاب‌شده
    PARENT → parent_content کامل همه parent_ids انتخاب‌شده
    MIXED  → parent_content برای parent_ids + child_content برای child_ids
    """
    parts = []

    if decision in ("PARENT", "MIXED"):
        for pid in parent_ids:
            parent = parents_map.get(pid)
            if parent:
                parts.append(
                    f"### [{parent.id}] {parent.title}\n{parent.content}"
                )

    if decision in ("CHILD", "MIXED"):
        id_set = set(child_ids)
        selected = [r for r in child_results if r.child_id in id_set]

        # fallback: اگر هیچ child مطابقت نداشت، همه را برگردان
        if not selected:
            selected = child_results

        for r in selected:
            parts.append(
                f"### [{r.child_id}] {r.child_title}\n{r.child_content}"
            )

    # fallback کلی: اگر parts خالی ماند
    if not parts:
        for r in child_results:
            parts.append(
                f"### [{r.child_id}] {r.child_title}\n{r.child_content}"
            )

    return "\n\n".join(parts)


# ──────────────────────── تابع اصلی ─────────────────────────────────

def decide_context(
    query: str,
    child_results,
    parents_map: dict,
) -> DecisionResult:
    """
    LangChain chain را صدا می‌زند و تصمیم می‌گیرد
    context نهایی CHILD / PARENT / MIXED باشد.

    پارامترها:
        query        : سؤال کاربر
        child_results: خروجی search_children
        parents_map  : دیکشنری {parent_id -> ParentChunk}
    """
    if not child_results:
        return DecisionResult(decision="CHILD", context="")

    formatted_chunks = _format_chunks(child_results)

    raw_output: str = _chain.invoke({
        "query": query,
        "formatted_chunks": formatted_chunks,
    })

    decision, parent_ids, child_ids = _parse_response(raw_output)

    context = _build_context(
        decision, parent_ids, child_ids, child_results, parents_map
    )

    return DecisionResult(
        decision=decision,
        parent_ids=parent_ids,
        child_ids=child_ids,
        context=context,
    )


# ──────────────────────────── چاپ ───────────────────────────────────

def print_decision_result(result: DecisionResult) -> None:
    """نتیجه تصمیم و context انتخاب‌شده را به‌صورت خوانا چاپ می‌کند."""
    print("=" * 60)
    print(f"تصمیم      : {result.decision}")
    if result.parent_ids:
        print(f"Parent IDs : {result.parent_ids}")
    if result.child_ids:
        print(f"Child IDs  : {result.child_ids}")
    print("=" * 60)
    print("Context نهایی:")
    print("-" * 60)
    print(result.context)
    print("=" * 60)