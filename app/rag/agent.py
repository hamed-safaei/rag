from app.rag.schema.graphstate import RAGState
from app.rag.graph import _rag_app



def run_rag_pipeline(query: str) -> RAGState:
    """
    کل جریان RAG را برای یک سؤال کاربر اجرا می‌کند و state نهایی
    (شامل answer, context, parent_ids, status, missing و ...) را
    برمی‌گرداند.
    """
    initial_state: RAGState = {
        "query": query,
        "child_results": [],
        "parent_ids": [],
        "context": "",
        "status": "",
        "missing": [],
        "missing_before_transform": [],
        "transform_tool_used": [],
        "transform_queries": [],
        "retried": False,
        "answer": "",
    }
    final_state = _rag_app.invoke(initial_state)
    return final_state
