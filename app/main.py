"""
FastAPI setup.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.dependencies import (startup_es_client, shutdown_es_client, startup_db_client,
                              shutdown_db_client)
from app.routers.datasets import router as datasets_router, datasets_router as datasets_list_router
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router


@asynccontextmanager
async def lifespan(application: FastAPI):
    """
    Manage database and elasticsearch lifecycle.
    :param application:
    :return:
    """
    await startup_db_client(application)
    await startup_es_client(application)
    yield
    await shutdown_db_client(application)
    await shutdown_es_client(application)

app = FastAPI(lifespan=lifespan)

@app.get("/health")
def health_check():
    """
    Health check endpoint for Kubernetes.
    :return:
    """
    return {"status": "ok"}

app.include_router(datasets_list_router)
app.include_router(datasets_router)
app.include_router(admin_router)

app.include_router(auth_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Validation exception handler. Prints more detailed information about request validation to the
    log.
    :param request:
    :param exc:
    :return:
    """
    print("--- 422 VALIDATION ERROR ---")
    print(exc.errors())
    print(request)
    print("----------------------------")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )
