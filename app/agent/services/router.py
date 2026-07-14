from app.agent.chians import router_chain
from app.agent.schema import RouteDecision, RouterOutput


def classify_query(query: str) -> RouteDecision:
    result: RouterOutput = router_chain.invoke({"query": query})
    return result.decision