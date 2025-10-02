"""
API endpoints for dealing with a dataset.
"""
from typing import Dict, List, Optional

import jsonpath
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, model_serializer

from app.dependencies import DatasetDep, TenantDbDep, ElasticIndexDep
from app.exceptions.search import UnknownFacetsException
from app.models import Facet, DetailProperty, ResultProperty, FacetType
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
    try:
        search_results = es_index.browse(struc.offset, struc.limit, filter_options)
    except UnknownFacetsException as e:
        raise HTTPException(status_code=400, detail={
            "error": "unknown_facets",
            "message": str(e),
            "facets": e.facets
        }) from e
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


class FacetResponse(Facet):
    """
    A facet in a response. Added some additional fields compared to the Facet model so the min/max
    values can also be returned.
    """
    min: Optional[int] = None
    max: Optional[int] = None
    step: Optional[int] = None
    tree: Optional[dict] = None

    @model_serializer
    def serialize(self):
        """
        Serialize
        :return:
        """
        data = {
            "property": self.property,
            "name": self.name,
            "type": self.type
        }
        if self.type == FacetType.RANGE:
            data['min'] = self.min
            data['max'] = self.max
            data['step'] = self.step
        if self.type == FacetType.TREE:
            data['tree'] = self.tree
        return data


@router.get("/facets")
async def get_facets(db: TenantDbDep, dataset: DatasetDep, es_index: ElasticIndexDep):
    """
    Get all facets for this dataset.
    :param es_index:
    :param db:
    :param dataset:
    :return:
    """
    cursor = db['facets'].find({
        "dataset_name": dataset.name
    })

    facets_data = await cursor.to_list()

    facets = {facet['property']: FacetResponse(**facet) for facet in facets_data}
    range_props = [facet.property for facet in facets.values() if facet.type == FacetType.RANGE]
    # tree_props = [facet.property for facet in facets.values() if facet.type == FacetType.TREE]

    if len(range_props) > 0:
        mins_maxes = es_index.get_min_max(range_props)

        for prop, data in mins_maxes.items():
            facets[prop].min = data['min']
            facets[prop].max = data['max']
            facets[prop].step = 1

    # for prop in tree_props:
    #     facets[prop].tree = es_index.get_tree(prop)

    return list(facets.values())


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
async def get_facet(es_index: ElasticIndexDep, facet: FacetRequestBody, db: TenantDbDep,
              dataset: DatasetDep):
    """
    Get options for a given facet
    :param db:
    :param dataset:
    :param es_index:
    :param facet:
    :return:
    """
    cursor = db['facets'].find({
        "dataset_name": dataset.name,
        "property": facet.name
    })
    facet_data = (await cursor.to_list())[0]
    facet_obj = Facet(**facet_data)
    filter_options = FilterOptions(facets=facet.facets, query=facet.query)
    try:
        if facet_obj.type == FacetType.RANGE:
            return es_index.get_min_max([facet.name])
        if facet_obj.type == FacetType.TREE:
            return es_index.get_tree(facet.name, facet.filter, filter_options)
        return es_index.get_facet(facet.name, facet.amount, facet.filter, filter_options)
    except UnknownFacetsException as e:
        raise HTTPException(status_code=400, detail={
            "error": "unknown_facets",
            "message": str(e),
            "facets": e.facets
        }) from e


class CreateFacetRequestBody(BaseModel):
    """
    Request body for facet creation.
    """
    property: str
    name: str
    type: str


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
