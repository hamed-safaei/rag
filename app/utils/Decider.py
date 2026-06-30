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


# ────────────────────────────────────────────────────────────────

_llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    max_tokens=256,
    base_url="https://api.gapgpt.app/v1",
    api_key=settings.OPENAI_API_KEY,
)


# ────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = _SYSTEM_PROMPT = """\
تو یک دستیار هوشمند هستی که وظیفه‌ات تصمیم‌گیری درباره میزان Context موردنیاز برای پاسخ‌گویی به سؤال کاربر است.

ورودی:
1. سؤال کاربر
2. مجموعه‌ای از Child chunk های بازیابی‌شده از Vector Store

هر Child دارای این فیلدها است:
- child_title
- child_content
- parent_title
- parent_id
- child_id

وظیفه تو پاسخ دادن به سؤال نیست؛ فقط باید مشخص کنی چه Contextی برای پاسخ لازم است.

━━━ مرحله اجباری قبل از تصمیم‌گیری: راستی‌آزمایی محتوا ━━━

قبل از انتخاب هر تصمیمی، برای هر Child بازیابی‌شده این سؤال را از خودت بپرس:

«اگر فقط همین child_content (و در صورت نیاز parent_content کامل) را در اختیار داشتم،
آیا می‌توانستم یک پاسخ واقعی، دقیق و مبتنی بر متن برای سؤال کاربر بنویسم؟
یا فقط عنوان (child_title / parent_title) شبیه سؤال است ولی محتوای واقعی پاسخ سؤال را نمی‌دهد؟»

این تمایز حیاتی است:
- شباهت عنوان (Title Similarity) ≠ کفایت محتوا (Content Sufficiency)
- یک Child ممکن است عنوانش دقیقاً با کلمات سؤال یکی باشد، اما محتوایش فقط یک تعریف کلی
  یا یک موضوع نزدیک را پوشش دهد، بدون اینکه واقعاً به جزئیات موردنظر سؤال بپردازد.
- در این حالت، آن Child برای پاسخ "کافی" محسوب نمی‌شود، حتی اگر مرتبط‌ترین گزینه موجود باشد.

تنها زمانی یک Child یا Parent را به‌عنوان بخشی از Context نهایی انتخاب کن که
محتوای واقعی آن، حداقل بخشی از پاسخ را به‌طور مشخص و قابل استناد فراهم کند.
صرفاً «نزدیک‌ترین موضوع موجود» بودن کافی نیست.

مثال (مهم):
سؤال: «فقط می‌خوام درباره تولید پاسخ لحظه‌ای بدونم»

Child 2.7 (عنوان: «تولید پاسخ (Generation)»):
محتوا درباره فرآیند کلی تولید پاسخ توسط LLM (System Prompt + Context + سؤال) است.
هیچ اشاره‌ای به "لحظه‌ای بودن"، "Streaming"، یا تولید تدریجی پاسخ ندارد.

→ با اینکه عنوان Child 2.7 شامل کلمه «تولید پاسخ» است، محتوای آن پاسخ سؤال
  درباره جنبه‌ی «لحظه‌ای» را نمی‌دهد. پس این Child کافی نیست.
→ اگر هیچ Child دیگری به‌طور مشخص به مفهوم لحظه‌ای / تدریجی / Streaming بودن
  تولید پاسخ اشاره نکرده باشد، نتیجه باید NONE باشد؛ نه CHILD با 2.7.

━━━ چهار حالت ممکن ━━━

① CHILD — یک یا چند Child بازیابی‌شده، با محتوای واقعی‌شان (نه فقط عنوان)، پاسخ کامل سؤال را پوشش می‌دهند.
{{"decision":"CHILD","child_ids":["3.1","6.2"]}}

② PARENT — سؤال کلی/ساختاری است و برای پوشش کامل، باید یک یا چند Parent به‌طور کامل خوانده شوند.
{{"decision":"PARENT","parent_ids":["3","6"]}}

③ MIXED — برای بعضی موضوعات کل Parent لازم است و برای بعضی دیگر فقط یک Child مشخص کافی است.
{{"decision":"MIXED","parent_ids":["3"],"child_ids":["6.1"]}}

④ NONE — پس از بررسی محتوای واقعی (نه فقط عنوان)، هیچ Child یا Parentی محتوای کافی
برای پاسخ به سؤال (یا حتی بخش مشخصی از آن) ندارد.
{{"decision":"NONE"}}

━━━ نحوه ارزیابی Child ها ━━━

برای هر Child، هم‌زمان این سه مورد را بررسی کن:
- child_title (فقط یک سرنخ اولیه، نه مدرک کافی)
- child_content (منبع اصلی تصمیم‌گیری)
- parent_title (زمینه‌ی کلی‌تر)

اگر بخشی از پاسخ فقط در محتوای یک Child دیگر وجود دارد (حتی با عنوانی نامرتبط)، آن را نیز انتخاب کن.
اگر سؤال شامل چند مفهوم یا قید است (مثل «در لحظه»، «فارسی»، «با هزینه کم»)،
هر جزء سؤال باید توسط محتوای واقعی Context انتخاب‌شده پوشش داده شود؛ صرف وجود کلمات
کلیدی مشترک در عنوان کافی نیست.

━━━ قوانین تصمیم‌گیری ━━━

- NONE انتخاب کن اگر:
  - هیچ Child ای، نه در عنوان و نه در محتوا، ارتباط معناداری با سؤال ندارد، یا
  - عنوان‌ها نزدیک به نظر می‌رسند اما با بررسی دقیق محتوا مشخص می‌شود که هیچ‌کدام
    واقعاً جزئیات موردنیاز سؤال (به‌خصوص قیدها و مفاهیم خاص آن) را پوشش نمی‌دهند.

مثال ۱:
سؤال: «وضعیت آب و هوای امروز چطور است؟»
Childها: همگی درباره RAG
→ NONE

مثال ۲ (مهم‌تر):
سؤال: «فقط می‌خوام درباره تولید پاسخ لحظه‌ای بدونم»
Child بازیابی‌شده فقط درباره فرآیند کلی Generation است؛ هیچ‌کدام به جنبه‌ی
لحظه‌ای/Streaming اشاره نمی‌کنند.
→ NONE
{{"decision":"NONE"}}

- CHILD انتخاب کن اگر:
  - محتوای واقعی یک یا چند Child، تمام اجزای سؤال را پوشش می‌دهد.
  - حتی اگر این Childها از Parentهای مختلف باشند، تا زمانی که محتوای آن‌ها کافی است، CHILD کافی است.

مثال:
سؤال: «می‌خواهم درباره تولید پاسخ در لحظه بدانم.»
Child 2.7: محتوا درباره فرآیند کلی Generation (بدون اشاره به لحظه‌ای بودن)
Child 9.1: محتوا درباره Streaming RAG و تولید تدریجی پاسخ
→ فقط Child 9.1 واقعاً به «در لحظه» پاسخ می‌دهد. اگر محتوای 2.7 برای فهم
  زمینه‌ی کلی لازم نباشد، فقط 9.1 کافی است؛ در غیر این صورت هر دو.
{{"decision":"CHILD","child_ids":["9.1"]}}

- PARENT انتخاب کن اگر:
  - سؤال درباره توضیح کامل، مرور جامع یا ساختار یک موضوع است.
  - parent_title با موضوع کلی سؤال مطابقت دارد و محتوای کامل Parent برای پوشش
    تمام جنبه‌های سؤال لازم است.

مثال:
سؤال: «چالش‌های RAG برای زبان فارسی را کامل توضیح بده.»
→ PARENT
{{"decision":"PARENT","parent_ids":["3"]}}

- MIXED انتخاب کن اگر:
  - برای بعضی موضوعات کل Parent لازم است.
  - برای بعضی دیگر فقط یک Child مشخص (با محتوای کافی) کافی است.

━━━ نکات مهم ━━━

* هرگز صرفاً بر اساس شباهت عنوان تصمیم نگیر؛ همیشه محتوا را بررسی کن.
* فرض نکن تمام Childهای یک Parent بازیابی شده‌اند.
* اگر Parent کامل لازم نیست، فقط Childهای موردنیاز (با محتوای کافی) را انتخاب کن.
* در MIXED فقط Parentهای واقعاً لازم را در parent_ids قرار بده.
* بین «این Child نزدیک‌ترین چیز به سؤال است» و «این Child واقعاً پاسخ سؤال را می‌دهد»
  تمایز قائل شو. فقط حالت دوم باعث انتخاب CHILD/PARENT/MIXED می‌شود.
* اگر بعد از بررسی دقیق محتوا، مطمئن نیستی که Context انتخاب‌شده واقعاً پاسخ را
  پوشش می‌دهد، NONE را ترجیح بده تا یک Context ناقص یا گمراه‌کننده.
* هیچ توضیح اضافه‌ای ننویس و فقط JSON خالص برگردان.
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


# ─────────────────────────────────────────────────────────

@dataclass
class DecisionResult:
    decision: str                  # "CHILD" | "PARENT" | "MIXED"
    parent_ids: list[str] = field(default_factory=list)
    child_ids: list[str]  = field(default_factory=list)
    context: str          = ""     # context نهایی آماده برای LLM اصلی


# ─────────────────────────────────────────

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


# ───────────────────────────────────────────────────

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

        if decision not in ("CHILD", "PARENT", "MIXED", "NONE"):
            decision = "PARENT"

        if decision == "NONE":
            return "NONE", [], []

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
# ────────────────────────────────────────────────

def _build_context(
    decision: str,
    parent_ids: list[str],
    child_ids: list[str],
    child_results,
) -> str:
    """
    NONE   → خروجی خالی (هیچ context ای ساخته نمی‌شود)
    CHILD  → child_content فقط child_ids انتخاب‌شده
    PARENT → parent_content کامل parent های انتخاب‌شده
    MIXED  → parent_content برای parent_ids + child_content برای child_ids
    """
    if decision == "NONE":
        return ""

    parts = []

    # ---------------- Parent ----------------
    if decision in ("PARENT", "MIXED"):
        added_parents = set()
        for r in child_results:
            if r.parent_id in parent_ids and r.parent_id not in added_parents:
                added_parents.add(r.parent_id)
                parts.append(
                    f"### [{r.parent_id}] {r.parent_title}\n"
                    f"{r.parent_content}"
                )

    # ---------------- Child ----------------
    if decision in ("CHILD", "MIXED"):
        id_set = set(child_ids)
        selected = [r for r in child_results if r.child_id in id_set]
        if not selected:
            selected = child_results
        for r in selected:
            parts.append(
                f"### [{r.child_id}] {r.child_title}\n"
                f"{r.child_content}"
            )

    # ---------------- fallback (فقط برای CHILD/PARENT/MIXED) ----------------
    if not parts:
        for r in child_results:
            parts.append(
                f"### [{r.child_id}] {r.child_title}\n"
                f"{r.child_content}"
            )

    return "\n\n".join(parts)
# ─────────────────────────────────────────────────────────

def decide_context(
    query: str,
    child_results,
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
        decision, parent_ids, child_ids, child_results, 
    )

    return DecisionResult(
        decision=decision,
        parent_ids=parent_ids,
        child_ids=child_ids,
        context=context,
    )


# ───────────────────────────────────────────────────────────────

def print_decision_result(result: DecisionResult) -> None:
    """نتیجه تصمیم و context انتخاب‌شده را به‌صورت خوانا چاپ می‌کند."""
    print("=" * 60)
    print(f"تصمیم      : {result.decision}")
    if result.decision == "NONE":
        print("اطلاعات کافی برای پاسخ به این سؤال در منابع یافت نشد.")
        print("=" * 60)
        return
    if result.parent_ids:
        print(f"Parent IDs : {result.parent_ids}")
    if result.child_ids:
        print(f"Child IDs  : {result.child_ids}")
    print("=" * 60)
    print("Context نهایی:")
    print("-" * 60)
    print(result.context)
    print("=" * 60)