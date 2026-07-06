import re
from app.models.Chunks import ChildChunk, ParentChunk
import fitz

CHILD_NUMERIC_PATTERN = re.compile(
    r'^[\u06F0-\u06F9۰-۹\d]+[\.\．][\u06F0-\u06F9۰-۹\d]+\s+\S'
)

def classify_block(text: str, font_size: float) -> str:
    text = text.strip()
    if font_size >= 19.0:
        return "parent"
    if CHILD_NUMERIC_PATTERN.match(text):
        return "child"
    return "body"  # الف) ب) و بقیه همه body

TITLE_PREFIX_PATTERN = re.compile(
    r"^\s*[\d۰-۹]+(?:[\.．][\d۰-۹]+)*\s*[\.．]?\s*"
)

def clean_title(title: str) -> str:
    """شماره ابتدای عنوان (مثل ۵. یا ۳.۲.) را حذف می‌کند."""
    return TITLE_PREFIX_PATTERN.sub("", title).strip()



def extract_blocks(path: str) -> list[dict]:
    doc = fitz.open(path)
    blocks = []
    for page_num, page in enumerate(doc, start=1):
        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:
                continue
            text, max_size = "", 0
            for line in block["lines"]:
                for span in line["spans"]:
                    text += span["text"] + " "
                    max_size = max(max_size, span["size"])
            text = text.strip()
            if text:
                blocks.append({"text": text, "font_size": round(max_size, 1),
                                "page": page_num, "type": classify_block(text, max_size)})
    return blocks



def build_chunks(path: str) -> list[ParentChunk]:
    blocks = extract_blocks(path)

    parents: list[ParentChunk] = []

    current_parent: ParentChunk | None = None
    current_child: ChildChunk | None = None

    parent_counter = 0
    child_counter = 0

    # متن‌های قبل از اولین Child واقعی
    pending_body: list[str] = []

    # آیا این Parent حداقل یک Child واقعی دارد؟
    has_real_child = False

    def flush_child():
        nonlocal current_child

        if current_parent is None or current_child is None:
            return

        current_parent.children.append(current_child)
        current_parent.content += "\n" + current_child.content
        current_child = None

    def flush_pending_as_intro():
        """متن‌های قبل از اولین Child واقعی را به عنوان مقدمه ذخیره می‌کند."""
        nonlocal child_counter

        if current_parent is None or not pending_body:
            return

        child_counter += 1

        intro = ChildChunk(
            id=f"{current_parent.id}.{child_counter}",
            title=f"مقدمه ای برای: {current_parent.title}",
            content="\n".join(pending_body),
            parent_id=current_parent.id,
        )

        current_parent.children.append(intro)
        current_parent.content += "\n" + intro.content

        pending_body.clear()

    def flush_pending_as_single_child():
        """اگر Parent هیچ Child واقعی نداشت، کل متن را یک Child می‌کند."""
        nonlocal child_counter

        if current_parent is None or not pending_body:
            return

        child_counter += 1

        only_child = ChildChunk(
            id=f"{current_parent.id}.{child_counter}",
            title=current_parent.title,
            content="\n".join(pending_body),
            parent_id=current_parent.id,
        )

        current_parent.children.append(only_child)
        current_parent.content += "\n" + only_child.content

        pending_body.clear()

    for block in blocks:

        btype = block["type"]
        text = block["text"]

        # ---------------- Parent ----------------
        if btype == "parent":

            flush_child()

            if current_parent is not None:

                if not has_real_child:
                    flush_pending_as_single_child()

                parents.append(current_parent)

            parent_counter += 1
            child_counter = 0

            current_parent = ParentChunk(
                id=str(parent_counter),
                title=clean_title(text),   # ← عنوان Parent بدون شماره
                content="",
            )

            pending_body.clear()
            has_real_child = False

        # ---------------- Child ----------------
        elif btype == "child":

            if current_parent is None:
                continue

            if not has_real_child:
                flush_pending_as_intro()

            has_real_child = True

            flush_child()

            child_counter += 1

            current_child = ChildChunk(
                id=f"{current_parent.id}.{child_counter}",
                title=clean_title(text),   # ← عنوان Child بدون شماره
                content=text,              # متن اصلی بدون تغییر
                parent_id=current_parent.id,
            )

        # ---------------- Body ----------------
        else:

            if current_parent is None:
                continue

            if not has_real_child and current_child is None:
                pending_body.append(text)
            else:
                if current_child is not None:
                    current_child.content += "\n" + text

    flush_child()

    if current_parent is not None:

        if not has_real_child:
            flush_pending_as_single_child()

        parents.append(current_parent)

    return parents