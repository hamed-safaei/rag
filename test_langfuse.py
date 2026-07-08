# from dotenv import load_dotenv
# import os

# load_dotenv()

# print("PUBLIC:", os.getenv("LANGFUSE_PUBLIC_KEY"))
# print("SECRET:", os.getenv("LANGFUSE_SECRET_KEY"))
# print("HOST:", os.getenv("LANGFUSE_HOST"))

# from langfuse import get_client

# langfuse = get_client()
# print(langfuse.auth_check())



from langfuse import observe

print(observe)