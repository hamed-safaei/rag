from pydantic import BaseModel, Field


class RAGState(BaseModel):
    query: str | None = None
    child_results: list = Field(default_factory=list)
    parent_ids: list[str] = Field(default_factory=list)
    context: str = ""
    status: str = ""
    missing: list[str] = Field(default_factory=list)
    missing_before_transform: list[str] = Field(default_factory=list)
    transform_tool_used: list[str] = Field(default_factory=list)
    transform_queries: list[str] = Field(default_factory=list)
    retried: bool = False
    answer: str = ""
