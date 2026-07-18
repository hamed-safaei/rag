"""
راه‌اندازی کلاینت LLM (از طریق LangChain / OpenAI-compatible API) و نسخه‌ی
structured-output آن که مستقیماً ClassificationResult برمی‌گرداند.
"""

import os
from langchain_openai import ChatOpenAI
# from app.core.config import Settings

from app.models.schemas.loader import ClassificationResult

import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

BASE_URL = "https://api.gapgpt.app/v1"

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0,
    base_url=BASE_URL,
    api_key=OPENAI_API_KEY,
)

structured_llm = llm.with_structured_output(ClassificationResult)