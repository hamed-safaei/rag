def make_batches_with_context(
    blocks: list[dict],
    batch_size: int = 45,
    overlap: int = 10,
) -> list[dict]:

    if overlap >= batch_size:
        raise ValueError("overlap باید کوچکتر از batch_size باشد")

    step = batch_size - overlap
    n = len(blocks)
    batches: list[dict] = []

    start = 0
    is_first = True

    while start < n:
        if is_first:
            context = []
            new_blocks = blocks[start: start + batch_size]
            window_end = start + batch_size
        else:
            context = blocks[start: start + overlap]
            new_blocks = blocks[start + overlap: start + batch_size]
            window_end = start + batch_size

        batches.append({"context": context, "new": new_blocks})

        if window_end >= n:
            break

        start += step
        is_first = False

    return batches





    """
    خروجی: لیستی از دیکشنری‌های {"context": [...], "new": [...]}

    - در batch اول: context خالی است، new شامل batch_size بلاک اول است.
    - در batch های بعدی: context شامل overlap بلاک آخرِ new دور قبل است
      (که قبلاً لیبل شده‌اند) و new شامل بلاک‌های واقعاً تازه است.

    مثال: batch_size=45, overlap=10  =>  step = 35
    batch1: new=[0:45]                context=[]
    batch2: new=[45:80]  context=[35:45]
    batch3: new=[80:115] context=[70:80]
    ...
    توجه: context و new هرگز index مشترک ندارند => امکان overwrite وجود ندارد.
    """