from app.data.Document import RAW_DOCUMENT
from app.models.Chunks import ParentChunk
from app.retriever.parent_child_retriever import ParentChildRetriever
from app.utils.Parser import parse_document


def print_structure(parents: list[ParentChunk]) -> None:
    """ساختار parent-child را به‌صورت درخت نمایش می‌دهد."""
    print("=" * 60)
    print("ساختار Parent-Child سند RAG فارسی")
    print("=" * 60)

    for parent in parents:
        preview = parent.content[:80].replace("\n", " ") + "..."
        print(f"\n📁 Parent [{parent.id}]: {parent.title}")
        print(f"   محتوا (پیش‌نمایش): {preview}")

        if parent.children:
            for child in parent.children:
                child_preview = child.content[:60].replace("\n", " ") + "..."
                print(f"   └─ Child [{child.id}]: {child.title}")
                print(f"             محتوا: {child_preview}")
        else:
            print("   └─ (بدون زیرعنوان)")

    total_children = sum(len(p.children) for p in parents)
    print("\n" + "=" * 60)
    print(f"✅ تعداد کل Parents  : {len(parents)}")
    print(f"✅ تعداد کل Children : {total_children}")
    print("=" * 60)


def demo_retrieval(retriever: ParentChildRetriever) -> None:
    """چند نمونه پرسش را اجرا و نتیجه را نمایش می‌دهد."""
    print("\n--- نمونه Retrieval ---")
    test_queries = ["Embedding", "فارسی", "ارزیابی"]

    for query in test_queries:
        print(f"\n🔍 پرسش: '{query}'")
        results = retriever.retrieve(query, top_k=2)

        if not results:
            print("  نتیجه‌ای یافت نشد.")
            continue

        for r in results:
            child = r["matched_child"]
            parent = r["parent"]
            print(f"  ↳ Child یافت‌شده : [{child.id}] {child.title}")
            if parent:
                print(f"     Parent برگشتی : [{parent.id}] {parent.title}")


def main() -> None:
    # ۱. پارس سند
    parents = parse_document(RAW_DOCUMENT)

    # ۲. نمایش ساختار
    print_structure(parents)

    # ۳. ساخت retriever
    retriever = ParentChildRetriever(parents)

    # ۴. نمونه retrieval
    demo_retrieval(retriever)

    print("\n✅ ساختار parent-child آماده است.")
    print("📌 مرحله بعدی: اضافه کردن embedding و vectorstore.")


if __name__ == "__main__":
    main()