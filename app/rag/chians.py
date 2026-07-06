from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from .prompts import (
decider_prompt , coverage_prompt , generator_prompt
)


from app.core.config import settings



BASE_URL = "https://api.gapgpt.app/v1"
API_KEY  = settings.OPENAI_API_KEY
MODEL    = "gpt-4o"





llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0.3,
    max_tokens=1024,
    base_url="https://api.gapgpt.app/v1",
    api_key=settings.OPENAI_API_KEY,
)


decider_chain = decider_prompt | llm | StrOutputParser()
coverage_chain = coverage_prompt | llm | StrOutputParser()
generator_chain = generator_prompt | llm | StrOutputParser()


