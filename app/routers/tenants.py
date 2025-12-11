"""
API endpoints for dealing with a tenant.
"""
from typing import Any

from fastapi import APIRouter

from app.dependencies import TenantDbDep

router = APIRouter(
    prefix="/api/tenants",
    tags=["tenants"]
)

@router.get("/current/datasets",
            description="Gets the available datasets for the current tenant",
            response_model=list[dict[str, Any]])
async def get_current_tenant_datasets(db: TenantDbDep):
    """
    Gets the datasets available for the current tenant.
    :return: list of available datasets and their data configuration details
    """
    cursor = db['datasets'].find({ 'tenant_name': db.name })
    selection = await cursor.to_list()

    return [ {
        "name": ds['name'],
        "data_configuration": ds['data_configuration'],
    } for ds in selection ]
