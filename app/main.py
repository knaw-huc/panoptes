"""
FastAPI setup.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.dependencies import (startup_es_client, shutdown_es_client, startup_db_client,
                              shutdown_db_client)
from .routers.datasets import router as datasets_router, datasets_router as datasets_list_router


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
