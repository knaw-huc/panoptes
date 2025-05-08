"""
FastAPI setup.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.dependencies import startup_es_client, shutdown_es_client, startup_db_client, shutdown_db_client
from .routers import datasets


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
app.include_router(datasets.router)
