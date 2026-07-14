# from langgraph.graph import StateGraph, END
# from app.agent.nodes import (
#     node_retrieve,
#     node_evaluate,
#     route_after_evaluate,
#     node_transform,
#     route_after_transform,
#     node_generate,
# )
# from app.agent.schema.graphstate import GraphState


# def build_graph():
#     workflow = StateGraph(GraphState)

#     workflow.add_node("retrieve", node_retrieve)
#     workflow.add_node("evaluate", node_evaluate)
#     workflow.add_node("transform", node_transform)
#     workflow.add_node("generate", node_generate)

#     workflow.set_entry_point("retrieve")
#     workflow.add_edge("retrieve", "evaluate")

#     workflow.add_conditional_edges(
#         "evaluate",
#         route_after_evaluate,
#         {
#             "transform": "transform",
#             "generate": "generate",
#         },
#     )

#     workflow.add_conditional_edges(
#         "transform",
#         route_after_transform,
#         {
#             "evaluate": "evaluate",
#             "generate": "generate",
#         },
#     )

#     workflow.add_edge("generate", END)

#     return workflow.compile()


# graph = build_graph()


from langgraph.graph import StateGraph, END
from app.agent.nodes import (
    node_route,
    node_retrieve,
    node_evaluate,
    route_after_evaluate,
    node_transform,
    route_after_transform,
    node_retrieve_done,
    node_history,
    node_generate,
)
from app.agent.schema.graphstate import GraphState


def build_graph():
    workflow = StateGraph(GraphState)

    workflow.add_node("route", node_route)
    workflow.add_node("retrieve", node_retrieve)
    workflow.add_node("evaluate", node_evaluate)
    workflow.add_node("transform", node_transform)
    workflow.add_node("retrieve_done", node_retrieve_done)
    workflow.add_node("history", node_history)
    workflow.add_node("generate", node_generate)

    workflow.set_entry_point("route")

    # fan-out: همیشه هر دو شاخه اجرا می‌شوند (نودها خودشان no-op بودن را مدیریت می‌کنند)
    workflow.add_edge("route", "retrieve")
    workflow.add_edge("route", "history")

    workflow.add_edge("retrieve", "evaluate")

    workflow.add_conditional_edges(
        "evaluate",
        route_after_evaluate,
        {
            "transform": "transform",
            "retrieve_done": "retrieve_done",
        },
    )

    workflow.add_conditional_edges(
        "transform",
        route_after_transform,
        {
            "evaluate": "evaluate",
            "retrieve_done": "retrieve_done",
        },
    )

    # fan-in: generate فقط بعد از تمام‌شدن هر دو شاخه اجرا می‌شود
    workflow.add_edge(["retrieve_done", "history"], "generate")

    workflow.add_edge("generate", END)

    return workflow.compile()


graph = build_graph()