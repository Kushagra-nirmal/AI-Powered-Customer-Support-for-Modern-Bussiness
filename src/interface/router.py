"""API v1 router configuration.

This module sets up the main API router and includes all sub-routers for different
endpoints like authentication, chatbot functionality, tickets, and merchant bridges.
"""

from fastapi import APIRouter

from src.interface.auth import router as auth_router
from src.interface.interaction import router as chatbot_router
from src.interface.tickets import router as tickets_router
from src.interface.merchants import router as merchants_router
from src.system.logs import logger

api_router = APIRouter()

# Include routers
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(chatbot_router, prefix="/chatbot", tags=["chatbot"])
api_router.include_router(tickets_router, prefix="/tickets", tags=["tickets"])
api_router.include_router(merchants_router, prefix="/merchants", tags=["merchants"])


@api_router.get("/health")
async def health_check():
    """Health check endpoint.

    Returns:
        dict: Health status information.
    """
    logger.info("health_check_called")
    return {"status": "healthy", "version": "1.0.0"}
