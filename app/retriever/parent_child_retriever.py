from typing import Optional

from app.models.Chunks import ChildChunk, ParentChunk


class ParentChildRetriever:
    """
    نگه‌دارنده ساختار parent-child و رابط جستجو.

    منطق اصلی:
    - جستجو روی children انجام می‌شود (اندازه کوچک‌تر، دقت بالاتر).
    - وقتی child یافت شد، parent کامل برگردانده می‌شود (context بزرگ‌تر).

    مرحله بعدی:
    - children به vectorstore اضافه می‌شوند (embedding می‌شوند).
    - parents فقط در docstore نگه‌داری می‌شوند (بدون embedding).
    - متد search_children با جستجوی برداری واقعی جایگزین می‌شود.
    """

    def __init__(self, parents: list[ParentChunk]):
        # ذخیره parents با کلید id
        self.parents: dict[str, ParentChunk] = {p.id: p for p in parents}

        # ذخیره children با کلید id
        self.children: dict[str, ChildChunk] = {}

        # ایندکس معکوس: child_id → parent_id
        self.child_to_parent: dict[str, str] = {}

        for parent in parents:
            for child in parent.children:
                self.children[child.id] = child
                self.child_to_parent[child.id] = parent.id

    def search_children(self, query: str, top_k: int = 3) -> list[ChildChunk]:
        """
        جستجوی keyword ساده در عنوان و محتوای children.
        (placeholder تا embedding در مرحله بعدی جایگزین شود)
        """
        query_lower = query.lower()
        results: list[tuple[int, ChildChunk]] = []

        for child in self.children.values():
            score = 0
            if query_lower in child.title.lower():
                score += 2
            if query_lower in child.content.lower():
                score += 1
            if score > 0:
                results.append((score, child))

        results.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in results[:top_k]]

    def get_parent_for_child(self, child_id: str) -> Optional[ParentChunk]:
        """با داشتن child_id، parent کامل را برمی‌گرداند."""
        parent_id = self.child_to_parent.get(child_id)
        return self.parents.get(parent_id) if parent_id else None

    def retrieve(self, query: str, top_k: int = 3) -> list[dict]:
        """
        جستجو در children، سپس parent کامل را برمی‌گرداند.
        این الگوی اصلی Parent-Child Retrieval است.

        Returns:
            list of dicts با کلیدهای:
              - matched_child: ChildChunk یافت‌شده
              - parent: ParentChunk والد
        """
        matched_children = self.search_children(query, top_k)
        results = []
        seen_parents: set[str] = set()

        for child in matched_children:
            parent = self.get_parent_for_child(child.id)
            results.append({
                "matched_child": child,
                "parent": parent,
            })
            if parent:
                seen_parents.add(parent.id)

        return results