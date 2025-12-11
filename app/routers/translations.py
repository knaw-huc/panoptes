"""
API endpoints for dealing with translations.
"""

from fastapi import APIRouter

from app.dependencies import TenantDbDep

router = APIRouter(
    prefix="/api/translations",
    tags=["translations"]
)

@router.get("/{locale}",
            name="Get translations for a given locale",
            description="Gets the translations for the given locale.",
            response_model=dict[str, str])
async def get_translations(locale: str, db: TenantDbDep):
    """
    Gets the translations available for the current tenant.
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
