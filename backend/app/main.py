from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.redis import close_redis
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.tenant import TenantContextMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    yield
    await close_redis()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(TenantContextMiddleware)

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/health")
    async def health():
        return {"status": "ok", "app": settings.app_name}

    return app


app = create_app()
