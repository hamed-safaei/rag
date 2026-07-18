"""
استخراج بلاک‌های متنی خام از یک فایل PDF تک‌ستونی، بدون هیچ لیبل‌گذاری
معنایی (parent/child/body). خروجی این ماژول ورودی مراحل بعدی (prompts,
batching, classifier) است.
"""

import fitz  # PyMuPDF


def extract_blocks(path: str, rtl: bool = True, y_tolerance: float = 3.0) -> list[dict]:
    """
    استخراج بلاک‌های متنی از یک PDF تک‌ستونی با حفظ ترتیب طبیعی خواندن.

    فرضیات:
    - سند تک‌ستونی است.
    - فقط متن ساده دارد (بدون چیدمان پیچیده، جدول یا چندستونه).

    ترتیب استخراج:
    1. از بالا به پایین (Y)
    2. در هر ردیف، از راست به چپ (برای فارسی) یا چپ به راست

    خروجی:
    [
        {
            "index": 0,
            "text": "...",
            "font_size": 16.0
        },
        ...
    ]
    """

    doc = fitz.open(path)
    blocks = []

    for page in doc:
        page_blocks = []

        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:
                continue

            text_parts = []
            max_font_size = 0.0

            for line in block["lines"]:
                for span in line["spans"]:
                    text_parts.append(span["text"])
                    max_font_size = max(max_font_size, span["size"])

            text = " ".join(text_parts).strip()

            if not text:
                continue

            page_blocks.append({
                "text": text,
                "font_size": round(max_font_size, 1),
                "bbox": block["bbox"],   # فقط برای مرتب‌سازی استفاده می‌شود
            })

        if not page_blocks:
            continue

        # مرتب‌سازی اولیه از بالا به پایین
        page_blocks.sort(key=lambda b: b["bbox"][1])

        # گروه‌بندی بلاک‌های هم‌ردیف
        rows = []
        current_row = [page_blocks[0]]

        for block in page_blocks[1:]:
            if abs(block["bbox"][1] - current_row[-1]["bbox"][1]) <= y_tolerance:
                current_row.append(block)
            else:
                rows.append(current_row)
                current_row = [block]

        rows.append(current_row)

        # مرتب‌سازی افقی هر ردیف
        for row in rows:
            row.sort(key=lambda b: b["bbox"][0], reverse=rtl)

            for block in row:
                blocks.append({
                    "text": block["text"],
                    "font_size": block["font_size"],
                })

    # اضافه کردن ایندکس نهایی
    result = []

    for idx, block in enumerate(blocks):
        result.append({
            "index": idx,
            "text": block["text"],
            "font_size": block["font_size"],
        })

    doc.close()
    return result