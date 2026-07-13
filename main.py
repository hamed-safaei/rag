from fastapi import FastAPI , Depends , Response , Request
from contextlib import asynccontextmanager
import uvicorn
from fastapi_swagger import patch_fastapi
from app.core import Base, app_engine
from app.api import api_router
from app.auth import get_current_username , get_auth_user 
from app.api.v1.dependencies import get_jwt_auth_user
from app.models.database import User


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(">>> Running lifespan startup...")
    yield
    print(">>> App shutting down...")


app = FastAPI(
    lifespan=lifespan,
    docs_url=None,
    swagger_ui_oauth2_redirect_url=None,
)



patch_fastapi(app, docs_url="/swagger")
app.include_router(api_router)




@app.get("/public")
def public_route():
    return {"message" : "This is a public route"}


# @app.get("/private/basic")
# def private_route(user : User = Depends(get_current_username)):
#     print(user.username)
#     return {"message" : "This is a private route"}


# @app.get("/private/token")
# def private_route(user = Depends(get_auth_user)):
#     print(user.username)
#     return {"message" : "This is a private route"}


@app.get("/private/token/jwt")
def private_route(user = Depends(get_jwt_auth_user)):
    print(user.id)
    return {"message" : "This is a private route"}



# @app.post("/set-cookie")
# def create_cookie(response: Response):
#     response.set_cookie(key="test", value="something")
#     return {"message": "Cookie Has Been Set"}


# @app.get("/get-cookie")
# def get_cookie(request: Request):
#     print(request.cookies.get('test'))
#     return {"message": "Cookie Has Been Set"}





if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8008)