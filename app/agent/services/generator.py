
from typing import Optional
from app.agent.chians import generator_chain


def generate_answer(
    query: str,
    context: str = "",
    history: Optional[str] = None,
) -> str:
    answer: str = generator_chain.invoke({
        "query": query,
        "context": context or "(بدون نتیجه‌ی جستجو)",
        "history": history ,
    })

    return answer.strip()