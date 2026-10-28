"""
Endpoints for managing the Panoptes system as a whole.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import MainDbDep, admin_domain, ElasticsearchDep
from app.models import Tenant
from app.models import FacetType
from app.services.authentication.authentication import is_admin

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(admin_domain), Depends(is_admin)],
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

# post en put voor nieuwe tenants
@router.post("/tenants")
async def post_tenants(db: MainDbDep, tenant: Tenant):
    """"
    Post new tenants.
    """
    try:
        db.tenants.insert_one(tenant.model_dump())
        print(f"added dataset '{tenant.name}' to tenant")
    except Exception as e:
        print(f"problem with dataset: {tenant}")
        print("valisation error details:", str(e))
        raise HTTPException(status_code=422, detail=str(e))


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
