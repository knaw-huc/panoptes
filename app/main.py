from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import TenantDbDep, shutdown_db_client, startup_db_client, ElasticIndexDep
from app.dependencies import startup_es_client, shutdown_es_client
from app.models import Dataset
from .routers import datasets


@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup_db_client(app)
    await startup_es_client(app)
    yield
    await shutdown_db_client(app)
    await shutdown_es_client(app)


app = FastAPI(lifespan=lifespan)

app.include_router(datasets.router)


@app.get('/')
async def index(database: TenantDbDep):
    items = await database['datasets'].find().to_list(None)
    return {'Hello': 'World', 'datasets': [Dataset(**item) for item in items]}
