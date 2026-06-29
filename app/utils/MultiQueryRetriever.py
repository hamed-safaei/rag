from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import settings
from app.utils.Retriever import search_children

# --------------------------------------------------

llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    base_url="https://api.gapgpt.app/v1",
    api_key=settings.OPENAI_API_KEY,
)

prompt = ChatPromptTemplate.from_template("""
تو یک دستیار برای سیستم RAG هستی.

برای سوال زیر 5 نسخه متفاوت و مناسب برای جستجو در Vector Database تولید کن.

فقط سوال‌ها را در خطوط جداگانه بنویس.
هیچ شماره‌گذاری یا توضیح اضافه ننویس.

سوال:
{question}
""")

generate_queries = (
    prompt
    | llm
    | StrOutputParser()
    | RunnableLambda(
        lambda x: [line.strip() for line in x.splitlines() if line.strip()]
    )
)

# --------------------------------------------------

def _search_queries(inputs):
    question = inputs["question"]
    queries = [question] + inputs["queries"]

    unique = {}

    for q in queries:
        docs = search_children(
            q,
            collection_name="loader",
            top_k=3,
        )

        for doc in docs:
            unique[doc.child_id] = doc

    return list(unique.values())


multi_query_retriever = (
    {
        "question": RunnableLambda(lambda x: x["question"]),
        "queries": generate_queries,
    }
    | RunnableLambda(_search_queries)
)