from pydantic import BaseModel, Field
from enum import Enum



class RouteDecision(str, Enum):
    history = "history"
    retrieve = "retrieve"
    both = "both"
    none = "none"


class RouterOutput(BaseModel):
    decision: RouteDecision = Field(description="دسته‌بندی نهایی پرسش کاربر")
