"""
API endpoints for dealing with translations.
"""

from fastapi import APIRouter

from app.dependencies import TenantDbDep

router = APIRouter(
    prefix="/api/translations",
    tags=["translations"]
)

@router.get("/{locale}", description="Gets the translations for the given locale")
async def get_datasets(locale: str, db: TenantDbDep):
    """
    Gets the datasets available for the current tenant.
    :return: object containing (label key, label value) pairs of the available
             translations given a locale string
    """
    cursor = db['translations'].find({ 'locale': locale })
    selection = await cursor.to_list()

    items = {
        doc['label_key']: doc['label_value']
        for doc in selection
    }

    return items
