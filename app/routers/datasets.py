from fastapi import APIRouter
from pydantic import BaseModel

from app import ElasticIndexDep

router = APIRouter(
    prefix="/datasets/{dataset_name}",
    tags=["datasets"]
)


class BrowseRequestBody(BaseModel):
    page: int
    page_length: int
    searchvalues: list


@router.get("/browse")
async def browse(es_index: ElasticIndexDep, struc: BrowseRequestBody):
    """
    Search for articles using elasticsearch.
    :return:
    """
    print(struc)
    ret_struc = es_index.browse(struc.page, struc.page_length, struc.searchvalues)
    print(ret_struc)
    return ret_struc
