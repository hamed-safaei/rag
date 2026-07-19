"""
پکیج loader: خط لوله‌ی کامل تبدیل PDF به ساختار سلسله‌مراتبی
Parent/Child برای استفاده در RAG.

جریان معمول استفاده:

    from app.services.loader import (
        extract_blocks,
        classify_document,
        build_hierarchy,
        prompt,
        structured_llm,
    )

    blocks = extract_blocks("document.pdf")

    classifier = prompt | structured_llm
    result = classify_document(blocks, classifier)

    parents = build_hierarchy(blocks, result)
"""

from .llm import llm, structured_llm
from .pdf_extractor import extract_blocks
from .prompts import prompt, STRUCTURE_PROMPT, build_blocks_prompt, build_context_prompt, build_hint
from .batching import make_batches_with_context
from .classifier import classify_document
from .hierachy_builder import build_hierarchy

__all__ = [
    "llm",
    "structured_llm",
    "BlockLabel",
    "ClassificationResult",
    "extract_blocks",
    "prompt",
    "STRUCTURE_PROMPT",
    "build_blocks_prompt",
    "build_context_prompt",
    "build_hint",
    "make_batches_with_context",
    "classify_document",
    "build_hierarchy",
]