from langfuse import observe
from sqlalchemy.orm import Session

from app.agent.graph import graph
from app.agent.schema.graphstate import GraphState


@observe()
def run_agent(query: str, session_id: str, db: Session) -> GraphState:
    initial_state: GraphState = {
        "query": query,
        "rewritten_query": "",
        "session_id": session_id,
        "route": "",
        "parent_ids": [],
        "child_ids": [],
        "context": "",
        "retried": False,
        "history": "",
        "answer": "",
        "child_records": [],
        "child_after_transform": [],
        "needs_retry": False,
    }

    return graph.invoke(
        initial_state,
        config={"configurable": {"db": db}},
    )