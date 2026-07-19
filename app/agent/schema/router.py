# from pydantic import BaseModel, Field
# from enum import Enum



# class RouteDecision(str, Enum):
#     history = "history"
#     retrieve = "retrieve"
#     both = "both"
#     none = "none"


# class RouterOutput(BaseModel):
#     decision: RouteDecision = Field(description="دسته‌بندی نهایی پرسش کاربر")




from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class RouteDecision(str, Enum):
    retrieve = "retrieve"
    generate = "generate"


class RouterOutput(BaseModel):
    decision: RouteDecision = Field(description="آیا برای پاسخ به سؤال نیاز به بازیابی هست یا نه")
    query: Optional[str] = Field(
        None,
        description="در صورت نیاز به بازیابی، پرسش نهایی برای جست‌وجو (در صورت وابستگی به تاریخچه، بازنویسی‌شده)",
    )