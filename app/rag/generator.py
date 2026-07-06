# app/rag/generator.py
#
# منبع اصلی: app/utils/generation.py
# فقط محل و نام فایل استاندارد شده؛ منطق بدون تغییر.

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import settings


# ────────────────────────────────────────────────────────────────

_llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0.3,
    max_tokens=1024,
    base_url="https://api.gapgpt.app/v1",
    api_key=settings.OPENAI_API_KEY,
)


# ────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """تو یک دستیار پاسخ‌گو در یک سیستم RAG هستی.
 
وظیفه تو این است که فقط بر اساس Context ارائه‌شده به سؤال کاربر پاسخ بدهی.
 
قوانین:
- فقط از اطلاعات موجود در Context استفاده کن. از دانش عمومی یا حدس خودت
  چیزی اضافه نکن.
- اگر Context خالی است یا پاسخ سؤال در آن وجود ندارد، صادقانه بگو که
  اطلاعات کافی برای پاسخ به این سؤال در منابع موجود نیست. چیزی نساز.
- پاسخ را روان، دقیق و به زبان فارسی بنویس.
- در صورت لزوم می‌توانی از چند بخش Context به‌طور هم‌زمان استفاده کنی.
"""


_HUMAN_TEMPLATE = """\
Context:
{context}

سؤال کاربر:
{query}
"""


_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM_PROMPT),
    ("human", _HUMAN_TEMPLATE),
])

_chain = _prompt | _llm | StrOutputParser()


# ─────────────────────────────────────────────────────────

_NO_CONTEXT_ANSWER = "اطلاعات کافی برای پاسخ به این سؤال در منابع موجود یافت نشد."


def generate_answer(query: str, context: str) -> str:
    """
    قسمت Generation (G) از RAG.

    بر اساس context ای که از decide_context به دست آمده، پاسخ نهایی را
    برای query تولید می‌کند.

    پارامترها:
        query   : سؤال کاربر
        context : خروجی result.context از decide_context

    اگر context خالی باشد (یعنی هیچ منبع مرتبطی پیدا نشده)، بدون صدا زدن
    مدل، مستقیماً یک پاسخ استاندارد «اطلاعات کافی نیست» برمی‌گرداند.
    """
    if not context or not context.strip():
        return _NO_CONTEXT_ANSWER

    answer: str = _chain.invoke({
        "query": query,
        "context": context,
    })

    return answer.strip()
