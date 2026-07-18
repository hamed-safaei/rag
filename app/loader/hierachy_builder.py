"""
تبدیل بلاک‌های لیبل‌گذاری‌شده (خروجی classify_document) به ساختار
سلسله‌مراتبی ParentChunk / ChildChunk که در بقیه‌ی پروژه (مثلاً برای
ایندکس‌کردن در RAG) استفاده می‌شود.
"""

from uuid import uuid4

from app.models.Chunks import ParentChunk, ChildChunk


def build_hierarchy(blocks, result):
    # index -> level
    labels = {
        item.index: item.level
        for item in result.labels
    }

    parents = []

    current_parent = None
    current_child = None

    for block in blocks:
        level = labels.get(block["index"], "body")
        text = block["text"]

        # ---------------- Parent ----------------
        if level == "parent":

            current_parent = ParentChunk(
                id=str(uuid4()),
                title=text,
                content="",
            )

            parents.append(current_parent)
            current_child = None

        # ---------------- Child ----------------
        elif level == "child":

            if current_parent is None:
                continue

            current_child = ChildChunk(
                id=str(uuid4()),
                title=text,
                content="",
                parent_id=current_parent.id,
            )

            current_parent.children.append(current_child)

            # عنوان Child هم داخل Parent.content ذخیره شود
            if current_parent.content:
                current_parent.content += "\n\n" + text
            else:
                current_parent.content = text

        # ---------------- Body ----------------
        else:

            if current_parent is None:
                continue

            # همیشه به محتوای Parent اضافه می‌شود
            if current_parent.content:
                current_parent.content += "\n" + text
            else:
                current_parent.content = text

            # اگر داخل Child هستیم، به Child هم اضافه می‌شود
            if current_child is not None:
                if current_child.content:
                    current_child.content += "\n" + text
                else:
                    current_child.content = text

    # اگر یک Parent هیچ Childـی نداشت، خودش را به‌عنوان تنها Child‌اش قرار بده
    for parent in parents:
        if not parent.children:
            parent.children.append(
                ChildChunk(
                    id=str(uuid4()),
                    title=parent.title,
                    content=parent.content,
                    parent_id=parent.id,
                )
            )

    return parents