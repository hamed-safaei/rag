from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser

from .prompts import (
    generator_prompt, evaluator_prompt, decompose_prompt, multiquery_prompt,
    router_prompt
)
from app.agent.schema import RouterOutput
from app.core.config import settings


BASE_URL = "https://api.gapgpt.app/v1"
API_KEY = settings.OPENAI_API_KEY


llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0,
    max_tokens=256,
    base_url=BASE_URL,
    api_key=API_KEY,
)

generator_llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0.3,
    max_tokens=1024,
    base_url=BASE_URL,
    api_key=API_KEY,
)



router_llm = llm.with_structured_output(RouterOutput)
router_chain = router_prompt | router_llm

evaluator_chain = evaluator_prompt | llm | JsonOutputParser()
generator_chain = generator_prompt | generator_llm | StrOutputParser()

decompose_chain = decompose_prompt | llm | StrOutputParser()
multiquery_chain = multiquery_prompt | llm | StrOutputParser()

