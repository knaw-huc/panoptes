from typing import Annotated, Optional, Type

from elasticsearch import Elasticsearch
from fastapi import Depends, HTTPException, Header
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.elastic_index import Index
from app.models import Tenant, Dataset

db_connection: Optional[AsyncIOMotorClient] = None
es_client: Optional[Elasticsearch] = None


async def startup_db_client(app) -> None:
    global db_connection
    db_connection = AsyncIOMotorClient(
        "mongodb://localhost:27017/",
    )

async def startup_es_client(app) -> None:
    global es_client
    es_client = Elasticsearch([{"scheme": "http", "host": "localhost", "port": 9200}])


async def shutdown_db_client(app) -> None:
    global db_connection
    db_connection.close()

async def shutdown_es_client(app) -> None:
    global es_client
    es_client.close()


def get_main_db() -> AsyncIOMotorDatabase:
    global db_connection
    return db_connection.get_database("main")


MainDbDep = Annotated[AsyncIOMotorClient, Depends(get_main_db)]


async def get_tenant(main_db: MainDbDep, host: Annotated[str | None, Header()] = None) -> Tenant:
    domain = host.split(":")[0]
    tenant = await main_db['tenants'].find_one({'domain': domain})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return Tenant(**tenant)


TenantDep = Annotated[Tenant, Depends(get_tenant)]



def get_tenant_db(tenant: TenantDep) -> AsyncIOMotorDatabase:
    global db_connection
    return db_connection.get_database(tenant.name)


TenantDbDep = Annotated[AsyncIOMotorClient, Depends(get_tenant_db)]


async def get_dataset(tenant_db: TenantDbDep, dataset_name: str) -> Dataset:
    dataset = await tenant_db['datasets'].find_one({'name': dataset_name})
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return Dataset(**dataset)

DatasetDep = Annotated[Dataset, Depends(get_dataset)]


def get_es_index(dataset: DatasetDep) -> Index:
    global es_client
    return Index(es_client, dataset.es_index)

ElasticIndexDep = Annotated[Index, Depends(get_es_index)]
