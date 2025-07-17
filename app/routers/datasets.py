"""
API endpoints for dealing with a dataset.
"""
from typing import Dict, List

import jsonpath
from fastapi import APIRouter
from pydantic import BaseModel

from app.dependencies import DatasetDep, TenantDbDep, ElasticIndexDep
from app.models import Facet, DetailProperty, ResultProperty
from app.services.search.elastic_index import FilterOptions
from app.services.datasets.connectors import DatasetConnectorDep

router = APIRouter(
    prefix="/api/datasets/{dataset_name}",
    tags=["datasets"]
)


class BrowseRequestBody(BaseModel):
    """
    Request body for searching in a dataset.
    """
    offset: int = 0
    limit: int = 10
    facets: Dict[str, list]
    query: str = ""


@router.post("/search")
async def browse(es_index: ElasticIndexDep, struc: BrowseRequestBody, db: TenantDbDep,
                 dataset: DatasetDep):
    """
    Search for articles using elasticsearch.
    :return:
    """
    print(struc)
    filter_options = FilterOptions(facets=struc.facets, query=struc.query)
    search_results = es_index.browse(struc.offset, struc.limit, filter_options)
    print(search_results)

    cursor = db.result_properties.find({
        "dataset_name": dataset.name
    }).sort("order")

    properties = await cursor.to_list()
    properties = [ResultProperty(**data) for data in properties]

    return {
        "amount": search_results.total_results,
        "pages": search_results.pages,
        "items": search_results.format_results(properties)
    }


@router.get("/facets")
async def get_facets(db: TenantDbDep, dataset: DatasetDep):
    """
    Get all facets for this dataset.
    :param db:
    :param dataset:
    :return:
    """
    cursor = db['facets'].find({
        "dataset_name": dataset.name
    })

    facets = await cursor.to_list()

    return [Facet(**facet) for facet in facets]


class FacetRequestBody(BaseModel):
    """
    Request body for retrieving facet options.
    """
    name: str
    amount: int
    filter: str
    facets: Dict[str, List[str]]
    query: str = ""
    sort: str


@router.post("/facet")
def get_facet(es_index: ElasticIndexDep, facet: FacetRequestBody):
    """
    Get options for a given facet
    :param es_index:
    :param facet:
    :return:
    """
    filter_options = FilterOptions(facets=facet.facets, query=facet.query)
    return es_index.get_facet(facet.name, facet.amount, facet.filter, filter_options)


class CreateFacetRequestBody(BaseModel):
    """
    Request body for facet creation.
    """
    property: str
    name: str
    type: str


# @router.post("/facets")
# async def create_facet(db: TenantDbDep, dataset: DatasetDep, facet_data: CreateFacetRequestBody):
#     """
#     Create a new facet for this dataset.
#     :param facet_data:
#     :param db:
#     :param dataset:
#     :return:
#     """
#     existing_facet = await db.facets.find_one({
#         "dataset_id": dataset.id,
#         "property": facet_data.property
#     })
#     if existing_facet:
#         raise HTTPException(
#             status_code=400,
#             detail=f"Facet for property {facet_data.property} already exists"
#         )
#
#     facet = Facet(
#         dataset_id=dataset.id,
#         property=facet_data.property,
#         name=facet_data.name,
#         type=FacetType(facet_data.type),
#     )
#
#     result = await db.facets.insert_one(facet.model_dump(by_alias=True, exclude={"id"}))
#     created_facet = await db.facets.find_one({"_id": result.inserted_id})
#
#     return {
#         "message": "facet created",
#         "facet": Facet(**created_facet),
#     }

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
        "dataset_name": dataset.name
    }).sort("order")

    properties = await cursor.to_list()
    properties = [DetailProperty(**data) for data in properties]

    return {
        "item_id": item_id,
        "item_data": [
            {
                "name": prop.name,
                "type": prop.type,
                "value": jsonpath.findall(prop.path, item_data)[0]
            } for prop in properties
        ]
    }
