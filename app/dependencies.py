"""
Dependencies for FastAPI to be used in the routers.
"""

from typing import Annotated

from elasticsearch import Elasticsearch
from fastapi import Depends, HTTPException, Header
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings, Settings
from app.elastic_index import Index
from app.models import Tenant, Dataset
from app.services.datasets.connectors import DatasetConnector, CMDIEditorConnector

database_connections = {}


async def startup_db_client(_app) -> None:
    """
    Init the MongoDB client.
    :param _app:
    :return:
    """
    settings = get_settings()
    database_connections["mongo"] = AsyncIOMotorClient(
        settings.mongo_connection,
    )

async def startup_es_client(_app) -> None:
    """
    Init the Elasticsearch connection.
    :param _app:
    :return:
    """
    settings = get_settings()

    database_connections["elastic"] = Elasticsearch([{
        "scheme": settings.es_scheme,
        "host": settings.es_host,
        "port": settings.es_port,

    }], basic_auth=(settings.es_username, settings.es_password)
    , verify_certs=False)


async def shutdown_db_client(_app) -> None:
    """
    Shut down the MongoDB client.
    :param _app:
    :return:
    """
    database_connections["mongo"].close()

async def shutdown_es_client(_app) -> None:
    """
    Close the Elasticsearch connection.
    :param _app:
    :return:
    """
    database_connections["elastic"].close()


SettingsDep = Annotated[Settings, Depends(get_settings)]

def get_main_db() -> AsyncIOMotorDatabase:
    """
    Get the main database, which contains information about the tenants using the app.
    :return:
    """
    return database_connections["mongo"].get_database("main")


MainDbDep = Annotated[AsyncIOMotorClient, Depends(get_main_db)]


async def get_tenant(main_db: MainDbDep, host: Annotated[str | None, Header()] = None) -> Tenant:
    """
    Get information about the current tenant, based on the domain name used to access the app.
    :param main_db:
    :param host:
    :return:
    """
    domain = host.split(":")[0]
    tenant = await main_db['tenants'].find_one({'domain': domain})
    if not tenant:
        raise HTTPException(status_code=404, detail="Domain name not known")
    return Tenant(**tenant)


TenantDep = Annotated[Tenant, Depends(get_tenant)]


def get_tenant_db(tenant: TenantDep) -> AsyncIOMotorDatabase:
    """
    Get the tenant specific database.
    :param tenant:
    :return:
    """
    return database_connections["mongo"].get_database(tenant.name)


TenantDbDep = Annotated[AsyncIOMotorClient, Depends(get_tenant_db)]


async def get_dataset(tenant_db: TenantDbDep, dataset_name: str) -> Dataset:
    """
    Get the dataset which is being used.
    :param tenant_db:
    :param dataset_name:
    :return:
    """
    dataset = await tenant_db['datasets'].find_one({'name': dataset_name})
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return Dataset(**dataset)

DatasetDep = Annotated[Dataset, Depends(get_dataset)]


def get_dataset_connector(dataset: DatasetDep) -> DatasetConnector:
    """
    Depends on the type
    :param dataset:
    :return:
    """
    if dataset.data_type == "cmdi":
        return CMDIEditorConnector(dataset.data_configuration)
    raise HTTPException(status_code=500, detail="Dataset misconfigured")

DatasetConnectorDep = Annotated[DatasetConnector, Depends(get_dataset_connector)]


def get_es_index(dataset: DatasetDep) -> Index:
    """
    Get the Elasticsearch index for the current dataset.
    :param dataset:
    :return:
    """
    return Index(database_connections["elastic"], dataset.es_index)

ElasticIndexDep = Annotated[Index, Depends(get_es_index)]
