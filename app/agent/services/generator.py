
from app.agent.chians import generator_chain



_NO_CONTEXT_ANSWER = "اطلاعات کافی برای پاسخ به این سؤال در منابع موجود یافت نشد."


def generate_answer(query: str, context: str) -> str:
    if not context or not context.strip():
        return _NO_CONTEXT_ANSWER

    answer: str = generator_chain.invoke({
        "query": query,
        "context": context,
    })

    return answer.strip()
