from sentence_transformers import CrossEncoder


# بارگذاری مدل Re-ranker
reranker = CrossEncoder(
    "BAAI/bge-reranker-v2-m3"
)


def rerank_results(query, child_results, top_k=5):
    
    # ساخت زوج‌های (Query, Document)
    pairs = []

    for item in child_results:
        document = f"""
        موضوع اصلی:
        {item.parent_title}

        بخش:
        {item.child_title}

        محتوا:
        {item.child_content}
        """

        pairs.append(
            (query, document)
        )


    # گرفتن امتیاز ارتباط
    scores = reranker.predict(pairs)


    # اضافه کردن امتیاز به نتایج
    ranked_results = []

    for item, score in zip(child_results, scores):
        ranked_results.append(
            {
                "parent_title": item.parent_title,
                "child_title": item.child_title,
                "child_content": item.child_content,
                "parent_id": item.parent_id,
                "child_id": item.child_id,
                "rerank_score": float(score)
            }
        )


    # مرتب سازی بر اساس امتیاز
    ranked_results = sorted(
        ranked_results,
        key=lambda x: x["rerank_score"],
        reverse=True
    )

    # فقط بهترین‌ها
    ranked_results = ranked_results[:top_k]

    # حذف score از خروجی
    for item in ranked_results:
        item.pop("rerank_score")

    return ranked_results