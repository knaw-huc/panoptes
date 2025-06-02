"""
API endpoints for dealing with a dataset.
"""
import jsonpath
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.dependencies import DatasetDep, TenantDbDep, ElasticIndexDep, DatasetConnectorDep
from app.models import Facet, DetailProperty

router = APIRouter(
    prefix="/datasets/{dataset_name}",
    tags=["datasets"]
)


class BrowseRequestBody(BaseModel):
    """
    Request body for searching in a dataset.
    """
    page: int
    page_length: int
    searchvalues: list


@router.post("/browse")
async def browse(es_index: ElasticIndexDep, struc: BrowseRequestBody):
    """
    Search for articles using elasticsearch.
    :return:
    """
    print(struc)
    ret_struc = es_index.browse(struc.page, struc.page_length, struc.searchvalues)
    print(ret_struc)
    return ret_struc


@router.get("/facets")
async def get_facets(db: TenantDbDep, dataset: DatasetDep):
    """
    Get all facets for this dataset.
    :param db:
    :param dataset:
    :return:
    """
    cursor = db['facets'].find({
        "dataset_id": dataset.id
    })

    facets = await cursor.to_list()

    return {
        "facets": [Facet(**facet) for facet in facets]
    }


class FacetRequestBody(BaseModel):
    """
    Request body for retrieving facet options.
    """
    name: str
    amount: int
    filter: str
    searchvalues: list
    sort: str


@router.post("/facet")
def get_facet(es_index: ElasticIndexDep, facet: FacetRequestBody):
    """
    Get options for a given facet
    :param es_index:
    :param facet:
    :return:
    """
    return es_index.get_facet(facet.name, facet.amount, facet.filter, facet.searchvalues)


class CreateFacetRequestBody(BaseModel):
    """
    Request body for facet creation.
    """
    property: str
    name: str
    type: str


@router.post("/facets")
async def create_facet(db: TenantDbDep, dataset: DatasetDep, facet_data: CreateFacetRequestBody):
    """
    Create a new facet for this dataset.
    :param facet_data:
    :param db:
    :param dataset:
    :return:
    """
    existing_facet = await db.facets.find_one({
        "dataset_id": dataset.id,
        "property": facet_data.property
    })
    if existing_facet:
        raise HTTPException(
            status_code=400,
            detail=f"Facet for property {facet_data.property} already exists"
        )

    facet = Facet(
        dataset_id=dataset.id,
        property=facet_data.property,
        name=facet_data.name,
        type=facet_data.type,
    )

    result = await db.facets.insert_one(facet.model_dump(by_alias=True, exclude={"id"}))
    created_facet = await db.facets.find_one({"_id": result.inserted_id})

    return {
        "message": "facet created",
        "facet": Facet(**created_facet),
    }

@router.get("/details/{item_id}")
async def by_id(dataset_connector: DatasetConnectorDep, dataset: DatasetDep,
                item_id: str, db: TenantDbDep):
    """
    Get details for a specific item.
    :param db:
    :param dataset:
    :param dataset_connector:
    :param item_id:
    :return:
    """
    item_data = dataset_connector.get_item(item_id)

    cursor = db.detail_properties.find({
        "dataset_id": dataset.id
    }).sort("order")

    properties = await cursor.to_list()
    properties = [DetailProperty(**data) for data in properties]

    return {
        "item_id": item_id,
        "item_data": [
            {
                "name": prop.name,
                "type": prop.type,
                "value": jsonpath.findall(prop.path, item_data)
            } for prop in properties
        ]
    }
