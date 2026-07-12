
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
            # ChildSearchResult یا هر آبجکتی با attributeهای مشابه
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
