from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from app.core.config import settings

BASE_URL = "https://api.gapgpt.app/v1"
API_KEY = settings.OPENAI_API_KEY

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0,
    base_url=BASE_URL,
    api_key=API_KEY,
)

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
تو وظیفه داری خلاصه‌ی مکالمه را به‌روز کنی.

اگر خلاصه‌ی قبلی وجود داشت:
- آن را به عنوان حافظه‌ی گفتگو در نظر بگیر.
- اطلاعات جدید را با آن ادغام کن.
- موارد تکراری را حذف کن.
- اگر اطلاعات جدید، اطلاعات قبلی را اصلاح می‌کند، نسخه‌ی جدید را نگه دار.

اگر خلاصه‌ی قبلی خالی بود:
- فقط مکالمه‌ی جدید را خلاصه کن.

قوانین:
- حداکثر 150 کلمه.
- خلاصه باید به فارسی باشد.
- تمام موضوعات مهم را پوشش بده.
- فقط خلاصه را برگردان و هیچ توضیح اضافه‌ای ننویس.
            """,
        ),
        (
            "human",
            """
خلاصه قبلی:

{history_summary}

---

پیام‌های جدید:

{conversation}
            """,
        ),
    ]
)

chain = prompt | llm | StrOutputParser()


def summarize(conversation: str, history_summary: str = "") -> str:
    return chain.invoke(
        {
            "conversation": conversation,
            "history_summary": history_summary,
        }
    )