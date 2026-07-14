from typing import Dict, List, Optional



def format_chunks(child_results) -> str:
    parts = []

    for r in child_results:
        if isinstance(r, dict):
            parent_title = r["parent_title"]
            child_title = r["child_title"]
            child_content = r["child_content"]
            parent_id = r["parent_id"]
            child_id = r["child_id"]
        else:
            parent_title = r.parent_title
            child_title = r.child_title
            child_content = r.child_content
            parent_id = r.parent_id
            child_id = r.child_id

        parts.append(
            f"parent title : {parent_title}\n"
            f"child title : {child_title}\n"
            f"child content :\n{child_content}\n"
            f"parent id : {parent_id}\n"
            f"child id : {child_id}"
        )

    return "\n\n---\n\n".join(parts)




def format_history(history: List[Dict[str, str]]) -> str:
    if not history:
        return "(تاریخچه‌ای موجود نیست)"

    lines = []
    for m in history:
        role = "کاربر" if m["role"] == "user" else "دستیار"
        lines.append(f"{role}: {m['content']}")

    return "\n\n".join(lines)
