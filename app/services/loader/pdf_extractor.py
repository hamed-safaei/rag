import fitz  # PyMuPDF


def extract_blocks(path: str, rtl: bool = True, y_tolerance: float = 3.0) -> list[dict]:
    """
    خروجی:
    [
        {
            "index": 0,
            "text": "..."
        }
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

            for line in block["lines"]:
                for span in line["spans"]:
                    text_parts.append(span["text"])

            text = " ".join(text_parts).strip()

            if not text:
                continue

            page_blocks.append({
                "text": text,
                "bbox": block["bbox"],  # فقط برای مرتب‌سازی
            })

        if not page_blocks:
            continue

        # مرتب‌سازی از بالا به پایین
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
                })

    result = [
        {
            "index": idx,
            "text": block["text"],
        }
        for idx, block in enumerate(blocks)
    ]

    doc.close()
    return result