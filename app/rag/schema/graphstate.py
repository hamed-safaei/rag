from pydantic import BaseModel, Field


class RAGState(BaseModel):
    query: str | None = None
    # سؤال اصلی کاربر (ثابت در طول گراف)

    child_results: list = Field(default_factory=list)
    # آخرین نتایج child بازیابی‌شده

    parent_ids: list[str] = Field(default_factory=list)
    # مجموع تمام parent_id هایی که تا الان context‌شان ساخته شده

    context: str = ""
    # context تجمعی نهایی

    status: str = ""
    # آخرین خروجی Coverage_Checker: COMPLETE / PARTIAL / NOT_FOUND

    missing: list[str] = Field(default_factory=list)
    # آخرین بخش‌های ناقص گزارش‌شده توسط Coverage_Checker

    missing_before_transform: list[str] = Field(default_factory=list)
    # همان missing ای که باعث ورود به مرحله‌ی transform شد؛ برخلاف
    # "missing" که بعد از دومین coverage check ممکن است خالی شود،
    # این فیلد ثابت می‌ماند تا مشخص باشد قبل از transform چه چیزی
    # ناقص تشخیص داده شده بود.

    transform_tool_used: list[str] = Field(default_factory=list)
    # به ازای هر آیتم از missing_before_transform، نام ابزاری که
    # route_query انتخاب کرده (multiquery یا decompose).

    transform_queries: list[str] = Field(default_factory=list)
    # مجموع تمام query/sub_query هایی که توسط transformer
    # (چه multiquery چه decompose) تولید شده‌اند.

    retried: bool = False
    # آیا یک دور transform را قبلاً طی کرده‌ایم؟

    answer: str = ""
    # پاسخ نهایی