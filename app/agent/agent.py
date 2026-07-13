from langfuse import observe

from app.agent.graph import graph
from app.agent.schema.graphstate import GraphState



@observe()
def run_agent(query: str) -> GraphState:
    initial_state: GraphState = {
        "query": query,
        "parent_ids": [],
        "child_ids": [],
        "context": "",
        "retried": False,
        "answer": "",
        "child_records": [],
        "child_after_transform": [],
        "needs_retry": False,
    }

    return graph.invoke(initial_state)