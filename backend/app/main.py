from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy import text

from app.config import get_settings
from app.models import Base
from app.utils.error_handler import register_exception_handlers
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Ensure SQLAlchemy models are registered before create_all.
    from app.models import menu, stall, user  # noqa: F401
    from app.repositories.postgres_repo import engine

    logger.info("Starting %s (env=%s)", settings.APP_NAME, settings.ENVIRONMENT)
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE stalls ADD COLUMN IF NOT EXISTS "
                "is_approved BOOLEAN NOT NULL DEFAULT TRUE"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_stalls_is_approved "
                "ON stalls (is_approved)"
            )
        )
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
        admin_controller,
        analytics_controller,
        auth_controller,
        delivery_controller,
        menu_controller,
        order_controller,
        review_controller,
        stall_controller,
        superadmin_controller,
        user_controller,
    )

    prefix = settings.API_PREFIX
    application.include_router(auth_controller.router, prefix=prefix)
    application.include_router(admin_controller.router, prefix=prefix)
    application.include_router(superadmin_controller.router, prefix=prefix)
    application.include_router(user_controller.router, prefix=prefix)
    application.include_router(stall_controller.router, prefix=prefix)
    application.include_router(menu_controller.router, prefix=prefix)
    application.include_router(order_controller.router, prefix=prefix)
    application.include_router(review_controller.router, prefix=prefix)
    application.include_router(delivery_controller.router, prefix=prefix)
    application.include_router(analytics_controller.router, prefix=prefix)

    return application


app = create_app()


@app.get("/admin", response_class=HTMLResponse, include_in_schema=False)
def admin_dashboard() -> str:
    return (STATIC_DIR / "admin.html").read_text(encoding="utf-8")


@app.get("/superadmin", response_class=HTMLResponse, include_in_schema=False)
def super_admin_dashboard() -> str:
    return (STATIC_DIR / "superadmin.html").read_text(encoding="utf-8")


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/", tags=["system"])
def root() -> dict:
    return {"app": settings.APP_NAME, "docs": "/docs", "health": "/health"}