"""
API endpoints for dealing with a dataset.
"""

from typing import Dict, List, Optional, Mapping, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, model_serializer

import jsonpath

from app.dependencies import DatasetDep, TenantDbDep, ElasticIndexDep
from app.exceptions.search import UnknownFacetsException
from app.models import Facet, DetailProperty, ResultProperty, FacetType
from app.services.search.elastic_index import FilterOptions
from app.services.datasets.connectors import DatasetConnectorDep
from app.tasks.tree_facets import construct_tree


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
            "type": self.type
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
    }).sort("order")

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
            # background_tasks.add_task(construct_tree, facet.name, dataset, db, es_index)
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

def python_type_to_schema_type(value: object) -> str:
    """Map Python types to JSON Schema 'type' values (for the $ case)."""
    checks = (
        (bool, "boolean"),
        (int, "integer"),
        (float, "number"),
        (list, "array"),
        (dict, "object"),
        (type(None), "null"),
    )

    for cls, name in checks:
        if isinstance(value, cls):
            return name

    return "string"

def _build_schema_for_value(value: Any, schemas_by_name: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively build a JSON-Schema-like structure for `value`,
    using `schemas_by_name` where keys match property names.

    - object -> {"type": "object", "properties": {...}}
    - array  -> {"type": "array", "items": {...}}
    - scalar -> {"type": "<inferred>"}
    """
    # Object: recurse into fields
    if isinstance(value, Mapping):
        properties: dict[str, Any] = {}

        for key, child in value.items():
            base = dict(schemas_by_name.get(key, {}) or {})
            child_schema = _build_schema_for_value(child, schemas_by_name)

            if isinstance(child, Mapping):
                base.setdefault("type", "object")
                if "properties" in child_schema:
                    nested = dict(base.get("properties", {}))
                    nested.update(child_schema["properties"])
                    base["properties"] = nested
            elif isinstance(child, list):
                base.setdefault("type", "array")
                base["items"] = child_schema
            else:
                base.setdefault("type", python_type_to_schema_type(child))

            properties[key] = base

        return { "type": "object", "properties": properties }

    # Array: use the first element as representative
    if isinstance(value, list):
        if not value:
            return { "type": "array", "items": {} }
        item_schema = _build_schema_for_value(value[0], schemas_by_name)
        return { "type": "array", "items": item_schema }

    # Scalar
    return { "type": python_type_to_schema_type(value) }


def _collect_object_schema(obj: Mapping[str, Any], schemas: dict[str, Any]) -> dict[str, Any]:
    """
    Build a schema dict for a single object based on its keys:
    { field_name: schema[field_name], ... } if present in schemas.
    """
    return {
        key: schemas[key]
        for key in obj.keys()
        if key in schemas
    }

@router.get("/details/{item_id}",
            summary="Get details for a specific item.")
async def by_id(dataset_connector: DatasetConnectorDep,
                dataset: DatasetDep,
                item_id: str,
                db: TenantDbDep):
    """
       Get details for a specific item.
       """
    # Get the full source object
    item_data = dataset_connector.get_item(item_id)

    # Load detail properties for this dataset (config lines with jsonpath)
    detail_props = [
        DetailProperty(**data)
        for data in await (
            db.detail_properties
              .find({"dataset_name": dataset.name})
              .sort("order")
              .to_list(length=None)
        )
    ]

    # Load schemas for this dataset (keyed by *property name*)
    schemas_by_name: dict[str, Any] = {
        doc["property"]: doc.get("schema")
        for doc in await (
            db.schema_properties
              .find({"dataset_name": dataset.name})
              .to_list(length=None)
        )
    }

    items: list[dict[str, Any]] = []
    for prop in detail_props:
        matches = jsonpath.findall(prop.path, item_data)
        if not matches:
            value: Any = None
        elif len(matches) == 1:
            value = matches[0]
        else:
            value = list(matches)

        resolved_type = prop.type  # default to configured type

        if value is None:
            resolved_schema: Any = None
        elif isinstance(value, (Mapping, list)):
            # objects / arrays: recursive schema from actual data
            resolved_schema = _build_schema_for_value(value, schemas_by_name)
            if resolved_type is None and isinstance(resolved_schema, Mapping):
                resolved_type = resolved_schema.get("type")
        else:
            # primitive: use per-property schema if present
            resolved_schema = dict(schemas_by_name.get(prop.name) or {})
            # ensure at least a type
            if "type" not in resolved_schema:
                resolved_schema["type"] = python_type_to_schema_type(value)

        # final fallback for type
        if resolved_type is None and value is not None:
            resolved_type = python_type_to_schema_type(value)

        items.append(
            {
                "name": prop.name,
                "type": resolved_type,
                "value": value,
                "schema": resolved_schema,
            }
        )

    return {
        "item_id": item_id,
        "item_data": items,
    }
