from langgraph.graph import StateGraph, END
from app.agent.nodes import node_retrieve ,node_evaluate,route_after_evaluate,node_transform,node_generate
from app.agent.schema.graphstate import GraphState


def build_graph():
    workflow = StateGraph(GraphState)

    workflow.add_node("retrieve", node_retrieve)
    workflow.add_node("evaluate", node_evaluate)
    workflow.add_node("transform", node_transform)
    workflow.add_node("generate", node_generate)

    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "evaluate")

    workflow.add_conditional_edges(
        "evaluate",
        route_after_evaluate,
        {
            "transform": "transform",
            "generate": "generate",
        },
    )

    workflow.add_edge("transform", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()


graph = build_graph()


