#generator.py


from app.rag.chians import generator_chain



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

    answer: str = generator_chain.invoke({
        "query": query,
        "context": context,
    })

    return answer.strip()
