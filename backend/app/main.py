from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models import Base
from app.utils.error_handler import register_exception_handlers
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Ensure SQLAlchemy models are registered before create_all.
    from app.models import menu, stall, user  # noqa: F401
    from app.repositories.postgres_repo import engine

    logger.info("Starting %s (env=%s)", settings.APP_NAME, settings.ENVIRONMENT)
    Base.metadata.create_all(bind=engine)
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(application)

    from app.controllers import (
        analytics_controller,
        auth_controller,
        delivery_controller,
        menu_controller,
        order_controller,
        review_controller,
        stall_controller,
        user_controller,
    )

    prefix = settings.API_PREFIX
    application.include_router(auth_controller.router, prefix=prefix)
    application.include_router(user_controller.router, prefix=prefix)
    application.include_router(stall_controller.router, prefix=prefix)
    application.include_router(menu_controller.router, prefix=prefix)
    application.include_router(order_controller.router, prefix=prefix)
    application.include_router(review_controller.router, prefix=prefix)
    application.include_router(delivery_controller.router, prefix=prefix)
    application.include_router(analytics_controller.router, prefix=prefix)

    return application


app = create_app()


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/", tags=["system"])
def root() -> dict:
    return {"app": settings.APP_NAME, "docs": "/docs", "health": "/health"}