"""
API endpoints for dealing with a dataset.
"""
from typing import Dict, List, Optional
from urllib.parse import urlparse
import logging

import boto3
from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, model_serializer

from app.dependencies import DatasetDep, TenantDbDep, ElasticIndexDep
from app.exceptions.search import UnknownFacetsException
from app.models import Facet, DetailProperty, ResultProperty, FacetType
from app.services.search.elastic_index import FilterOptions
from app.services.datasets.connectors import DatasetConnectorDep
from app.tasks.tree_facets import construct_tree

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)-5s %(name)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/datasets/{dataset_name}",
    tags=["datasets"]
)

datasets_router = APIRouter(
    prefix="/api/datasets",
    tags=["datasets"]
)


class DatasetSummary(BaseModel):
    """
    Public summary of a dataset (excludes sensitive configuration).
    """
    name: str
    data_type: str
    data_configuration: object


@datasets_router.get("")
async def list_datasets(db: TenantDbDep) -> list[DatasetSummary]:
    """
    Get all available datasets for this tenant.
    """
    cursor = db['datasets'].find({})
    datasets = await cursor.to_list()
    return [
        DatasetSummary(
            name=d['name'],
            data_type=d['data_type'],
            data_configuration={
                k: v for k, v in d['data_configuration'].items()
                if k not in {'s3_key_id', 's3_secret', 's3_endpoint'}
            }
        )
        for d in datasets
    ]

class BrowseRequestBody(BaseModel):
    """
    Request body for searching in a dataset.
    """
    offset: int = 0
    limit: int = 10
    facets: Dict[str, list]
    query: str = ""

class ResolveRequestBody(BaseModel):
    """
    Resolved resource details.
    """
    resource: str

@router.post("/resolve")
async def resolve(dataset: DatasetDep, request: ResolveRequestBody):
    """
    Resolve a ref for an external resource.

    Currently, this only supports S3 buckets, and for those the
    function creates a signed url the client can use to retrieve
    the resource.

    If credentials config is missing, this function raises a 500 error.
    If the input is invalid, this function raises a 400 error.

    :return: object containing resolved resource details (currently an URL)
    """
    config = dataset.data_configuration

    if not all([config.get('s3_key_id'), config.get('s3_secret'), config.get('s3_endpoint')]):
        raise HTTPException(status_code=500, detail={"error": "Missing configuration"})

    if request.resource is None or not request.resource.lower().startswith("s3://"):
        raise HTTPException(status_code=400, detail={"error": "Invalid parameters"})

    logger.info("Resolving resource: '%s' for dataset: '%s'", request.resource, dataset.name)

    parsed = urlparse(request.resource)
    bucket = parsed.netloc
    path = parsed.path.lstrip('/')
    logger.info("Resolved bucket: %s, path: %s", bucket, path)

    s3 = boto3.client(
        "s3",
        aws_access_key_id=config['s3_key_id'],
        aws_secret_access_key=config['s3_secret'],
        endpoint_url=config['s3_endpoint']
    )
    url = s3.generate_presigned_url(
        ClientMethod='get_object',
        Params={'Bucket': bucket, 'Key': path},
        ExpiresIn=3600
    )
    logger.info("Created signed url: %s", url)
    return {
        "url": url
    }

@router.post("/search")
async def browse(es_index: ElasticIndexDep, struc: BrowseRequestBody, db: TenantDbDep,
                 dataset: DatasetDep):
    """
    Search for articles using elasticsearch.
    :return:
    """
    filter_options = FilterOptions(facets=struc.facets, query=struc.query)
    try:
        search_results = es_index.browse(struc.offset, struc.limit, filter_options)
    except UnknownFacetsException as e:
        raise HTTPException(status_code=400, detail={
            "error": "unknown_facets",
            "message": str(e),
            "facets": e.facets
        }) from e

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
    order: int = 0

    @model_serializer
    def serialize(self):
        """
        Serialize
        :return:
        """
        data = {
            "property": self.property,
            "name": self.name,
            "type": self.type,
            "startOpen": self.start_open,
        }
        if self.type in [FacetType.RANGE, FacetType.HISTOGRAM]:
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

    facets = {facet['property']: Facet(**facet) for facet in facets_data}
    facet_responses = {facet['property']: FacetResponse(**facet) for facet in facets_data}
    range_props = [
        facet.property for facet in facets.values()
        if facet.type in [FacetType.RANGE, FacetType.HISTOGRAM]
    ]

    if len(range_props) > 0:
        mins_maxes = es_index.get_min_max(range_props)

        for prop, data in mins_maxes.items():
            facet = facets[prop]
            facet_responses[prop].min = data['min']
            facet_responses[prop].max = data['max']
            facet_responses[prop].step = 1

    response = list(facet_responses.values())
    response.sort(key=lambda facet: facet.order)

    return response


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


@router.post("/facet/{name}")
async def get_facet(name: str, es_index: ElasticIndexDep, facet: FacetRequestBody, db: TenantDbDep,
              dataset: DatasetDep):
    """
    Get options for a given facet
    :param name:
    :param db:
    :param dataset:
    :param es_index:
    :param facet:
    :return:
    """
    cursor = db['facets'].find({
        "dataset_name": dataset.name,
        "property": name
    })
    facet_data = (await cursor.to_list())[0]
    facet_obj = Facet(**facet_data)
    filter_options = FilterOptions(facets=facet.facets, query=facet.query)
    try:
        if facet_obj.type == FacetType.RANGE:
            return es_index.get_min_max([facet.name])
        if facet_obj.type == FacetType.TREE:
            return es_index.get_tree(facet_obj, filter_options)
        return es_index.get_facet(facet_obj, facet.amount, facet.filter, filter_options)
    except UnknownFacetsException as e:
        raise HTTPException(status_code=400, detail={
            "error": "unknown_facets",
            "message": str(e),
            "facets": e.facets
        }) from e


@router.get("/facet/{name}/tree")
async def get_tree(name: str, db: TenantDbDep, dataset: DatasetDep,
             parent: str | None = None):
    """
    Endpoint for lazy loading tree filters.
    :param name:
    :param db:
    :param dataset:
    :param parent: Query param: parent value to get children from
    :return:
    """
    cursor = db['nodes'].find({
        "dataset": dataset.name,
        "facet_name": name,
        "parent": parent,
    })
    nodes = await cursor.to_list()
    return {
        "nodes": [
            {
                "property": node["facet_name"],
                "name": node["name"],
                "value": node["value"],
                "parent": node["parent"],
                "hasChildren": node["has_children"]
            }
            for node in nodes
        ],
    }


@router.post("/facet/{name}/rebuild", status_code=status.HTTP_202_ACCEPTED)
def rebuild_tree(name: str, background_tasks: BackgroundTasks, db: TenantDbDep, dataset: DatasetDep,
                 es_index: ElasticIndexDep):
    """
    Rebuild the tree for a given facet.
    :param dataset:
    :param db:
    :param es_index:
    :param name:
    :param background_tasks:
    :return:
    """
    background_tasks.add_task(construct_tree, name, dataset, db, es_index)
    return {
        "name": name,
        "message": "rebuild tree scheduled"
    }


class CreateFacetRequestBody(BaseModel):
    """
    Request body for facet creation.
    """
    property: str
    name: str
    type: str


def process_property(prop: DetailProperty, item_data: Dict, data_configuration: Dict[str, str]):
    """

    :param prop:
    :param item_data:
    :param data_configuration:
    :return:
    """
    value = prop.render_value(item_data)

    if value is None:
        return {
            "name": prop.name,
            "type": prop.type,
            "value": None
        }

    if prop.type == 'image_s3':
        # Get signed URL from s3
        s3 = boto3.client(
            "s3",
            aws_access_key_id=data_configuration['s3_key_id'],
            aws_secret_access_key=data_configuration['s3_secret'],
            endpoint_url=data_configuration['s3_endpoint']
        )
        value_without_prefix = value[5:]
        bucket, path = value_without_prefix.split('/', 1)
        print(f"Bucket: {bucket}, Path: {path}")
        signed_url = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': bucket, 'Key': path},
            ExpiresIn=3600
        )
        value = signed_url

    return {
        "name": prop.name,
        "type": prop.type,
        "config": prop.config,
        "value": value
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
        "dataset_name": dataset.name
    }).sort("order")

    properties = await cursor.to_list()
    properties = [DetailProperty(**data) for data in properties]

    return {
        "item_id": item_id,
        "item_data": [
            process_property(prop, item_data, dataset.data_configuration) for prop in properties
        ]
    }
