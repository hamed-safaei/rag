from .batching import make_batches_with_context
from .prompts import build_blocks_prompt, build_context_prompt, build_hint
from app.models.schemas.loader import BlockLabel, ClassificationResult


def classify_document(
    blocks: list[dict],
    classifier,               # = prompt | structured_llm
    batch_size: int = 45,
    overlap: int = 10,
):
    blocks_by_index = {b["index"]: b for b in blocks}
    batches = make_batches_with_context(blocks, batch_size=batch_size, overlap=overlap)

    final_labels: dict[int, str] = {}

    for batch_num, batch in enumerate(batches, start=1):
        context_blocks = batch["context"]
        new_blocks = batch["new"]
        new_indices = {b["index"] for b in new_blocks}

        hint_text = build_hint(blocks_by_index, final_labels)
        context_prompt_text = build_context_prompt(context_blocks, final_labels)
        new_prompt_text = build_blocks_prompt(new_blocks)

        result = classifier.invoke(
            {
                "hint": hint_text,
                "context_blocks": context_prompt_text,
                "new_blocks": new_prompt_text,
            }
        )

        # --- فیلتر سخت‌گیرانه ---
        # فقط لیبل بلاک‌هایی که واقعاً جزو "new" این دور بودند را commit کن.
        # هر چیزی خارج از new_indices (مثلاً لیبل اشتباهیِ یک context block)
        # به‌طور کامل نادیده گرفته می‌شود و هرگز چیزی overwrite نمی‌شود.
        got_indices = set()
        for item in result.labels:
            if item.index in new_indices:
                final_labels[item.index] = item.level
                got_indices.add(item.index)

        # اگر مدل برای بعضی از بلاک‌های جدید خروجی نداد، پیش‌فرض امن body
        missing = new_indices - got_indices
        for idx in missing:
            final_labels[idx] = "body"

        print(
            f"[batch {batch_num}/{len(batches)}] "
            f"context={len(context_blocks)} new={len(new_blocks)} "
            f"missing={len(missing)}"
        )

    labels_list = [
        BlockLabel(index=idx, level=level)
        for idx, level in sorted(final_labels.items())
    ]

    return ClassificationResult(labels=labels_list)