from langgraph.graph import StateGraph, END
from app.agent.nodes import (
    node_history,
    node_route,
    route_after_route,
    node_retrieve,
    node_evaluate,
    route_after_evaluate,
    node_transform,
    route_after_transform,
    node_generate,
)
from app.agent.schema.graphstate import GraphState


def build_graph():
    workflow = StateGraph(GraphState)

    workflow.add_node("history", node_history)
    workflow.add_node("route", node_route)
    workflow.add_node("retrieve", node_retrieve)
    workflow.add_node("evaluate", node_evaluate)
    workflow.add_node("transform", node_transform)
    workflow.add_node("generate", node_generate)

    workflow.set_entry_point("history")
    workflow.add_edge("history", "route")

    workflow.add_conditional_edges(
        "route",
        route_after_route,
        {
            "retrieve": "retrieve",
            "generate": "generate",
        },
    )

    workflow.add_edge("retrieve", "evaluate")

    workflow.add_conditional_edges(
        "evaluate",
        route_after_evaluate,
        {"transform": "transform", "generate": "generate"},
    )

    workflow.add_conditional_edges(
        "transform",
        route_after_transform,
        {"evaluate": "evaluate" , "generate": "generate"},
    )

    workflow.add_edge("generate", END)

    return workflow.compile()


graph = build_graph()