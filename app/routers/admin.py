from fastapi import APIRouter, Depends

from app.dependencies import MainDbDep, admin_domain, ElasticsearchDep
from app.models import Tenant
from app.models import FacetType

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(admin_domain)],
)

@router.get("/tenants")
async def get_tenants(db: MainDbDep):
    """
    Get all tenants.
    :return:
    """
    tenants = db.tenants.find()
    tenant_list = [Tenant(**tenant) for tenant in await tenants.to_list()]
    print(tenant_list)
    return {"tenants": tenant_list}


@router.get("/indices")
async def get_indices(elasticsearch: ElasticsearchDep):
    """
    Get all available ES indices in this configuration.
    :return:
    """
    indices = elasticsearch.indices.get_alias(index="*", expand_wildcards="open").keys()

    return {
        "indices": sorted(list(indices))
    }


@router.get("/facettypes")
async def get_facet_types():
    """
    Get available types for facets
    :return:
    """
    return {
        "facetTypes": list(FacetType)
    }