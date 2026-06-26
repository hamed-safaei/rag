import re
from typing import Optional

from app.models.Chunks import ChildChunk, ParentChunk


def parse_document(raw_text: str) -> list[ParentChunk]:
    """
    متن سند را خوانده و ساختار parent-child می‌سازد.

    قراردادهای مارکرگذاری:
      === N === عنوان    →  Parent  (عنوان اصلی)
      --- N.M --- عنوان →  Child   (زیرعنوان)
    """
    lines = raw_text.strip().splitlines()

    parents: list[ParentChunk] = []
    current_parent: Optional[ParentChunk] = None
    current_child: Optional[ChildChunk] = None
    current_lines: list[str] = []

    def flush_child():
        """محتوای جاری را در child فعلی ذخیره می‌کند."""
        nonlocal current_child, current_lines
        if current_child is not None:
            current_child.content = "\n".join(current_lines).strip()
            current_parent.children.append(current_child)
            current_child = None
            current_lines = []

    def flush_parent_body():
        """محتوای بین عنوان parent و اولین child را در content والد می‌گذارد."""
        nonlocal current_lines
        if current_parent is not None and not current_parent.children and current_lines:
            current_parent.content = "\n".join(current_lines).strip()
            current_lines = []

    for line in lines:
        line = line.strip()

        # ── parent header ──
        parent_match = re.match(r"^===\s*([\d]+)\s*===\s*(.+)$", line)
        if parent_match:
            flush_child()
            flush_parent_body()
            if current_parent:
                _rebuild_parent_content(current_parent)
                parents.append(current_parent)

            pid = parent_match.group(1).strip()
            ptitle = parent_match.group(2).strip()
            current_parent = ParentChunk(id=pid, title=ptitle, content="")
            current_lines = []
            continue

        # ── child header ──
        child_match = re.match(r"^---\s*([\d]+\.[\d]+)\s*---\s*(.+)$", line)
        if child_match:
            flush_child()
            flush_parent_body()
            cid = child_match.group(1).strip()
            ctitle = child_match.group(2).strip()
            current_child = ChildChunk(
                id=cid,
                title=ctitle,
                content="",
                parent_id=current_parent.id if current_parent else "",
            )
            current_lines = []
            continue

        # ── خط معمولی ──
        current_lines.append(line)

    # flush آخرین‌ها
    flush_child()
    flush_parent_body()
    if current_parent:
        _rebuild_parent_content(current_parent)
        parents.append(current_parent)

    return parents


def _rebuild_parent_content(parent: ParentChunk) -> None:
    """
    محتوای کامل parent را از content مستقیم + محتوای همه children می‌سازد.
    این همان چیزی است که در retrieval به‌عنوان context بزرگ‌تر برگردانده می‌شود.
    """
    parts = []
    if parent.content:
        parts.append(parent.content)
    for child in parent.children:
        parts.append(f"[{child.id}] {child.title}\n{child.content}")
    parent.content = "\n\n".join(parts)