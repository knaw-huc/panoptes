from fastapi import APIRouter

from app.dependencies import TenantDbDep

router = APIRouter(
    prefix="/api/tenants",
    tags=["tenants"]
)

@router.get("/current/datasets", description="Gets the available datasets for the current tenant")
async def get_datasets(db: TenantDbDep):
    cursor = db['datasets'].find({ 'tenant_name': db.name })
    selection = await cursor.to_list()
    return [ {
        "name": ds['name'],
        "data_configuration": ds['data_configuration'],
    } for ds in selection ]
