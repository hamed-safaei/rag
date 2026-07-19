from pydantic import BaseModel, Field
from typing import Literal


class BlockLabel(BaseModel):
    index: int = Field(
        ...,
        description="ایندکس بلاک ورودی"
    )

    level: Literal["parent", "child", "body"] = Field(
        ...,
        description="نوع بلاک"
    )


class ClassificationResult(BaseModel):
    labels: list[BlockLabel]