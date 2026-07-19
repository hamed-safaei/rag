from app.agent.chians import router_chain
from app.agent.schema import RouterOutput


def classify_query(query: str, history: str = "") -> RouterOutput:
    result: RouterOutput = router_chain.invoke({
        "query": query,
        "history": history or "(تاریخچه‌ای وجود ندارد)",
    })
    return result