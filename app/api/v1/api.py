from fastapi import APIRouter

from app.api.v1.routers import (
    # sessions_router,
    # chat_router,
    # # agent_router,
    # # users_router,
    # connection_router ,
    auth_router , 
    # feedbacks_router
)

api_router = APIRouter(prefix="/api/v1")

# api_router.include_router(sessions_router)
# api_router.include_router(chat_router)
# api_router.include_router(feedbacks_router)
# # api_router.include_router(users_router)
# # api_router.include_router(agent_router)
# api_router.include_router(connection_router)
api_router.include_router(auth_router)