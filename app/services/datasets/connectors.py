"""
Implementation specific classes for dealing with dataset connections.
"""

from abc import ABC, abstractmethod
from typing import Annotated

import requests
from fastapi import HTTPException, Depends

from app.dependencies import DatasetDep, ElasticIndexDep
from app.models import Dataset
from app.services.search.elastic_index import Index


class DatasetConnector(ABC):
    """
    Base class for all datasets connectors.
    """
    @abstractmethod
    def __init__(self, dataset: Dataset) -> None:
        """
        Initialize a dataset connector instance. Always has a configuration dictionary as argument.
        Implementation is dataset type dependent.
        :param dataset:
        """

    @abstractmethod
    def get_item(self, identifier: str):
        """
        Geta specific item by id
        :param identifier:
        :return:
        """


class CMDIEditorConnector(DatasetConnector):
    """
    Connector using the API of the CMDI Forms editor
    """
    api_base: str
    id_property: str
    dataset: Dataset
    es_index: Index

    def __init__(self, dataset: Dataset, es_index: Index) -> None:
        self.dataset = dataset
        self.api_base = dataset.data_configuration["base_url"]
        self.id_property = dataset.data_configuration["id_property"]
        self.es_index = es_index


    def get_item(self, identifier: str):
        item = self.es_index.by_identifier(identifier, self.dataset.detail_id)
        item_id = item.get_prop(self.id_property)

        try:
            request = requests.get(f"{self.api_base}/{item_id}", headers={
                "Accept": "application/json"
            }, timeout=5)
        except requests.exceptions.Timeout as exc:
            raise HTTPException(status_code=504, detail="External source timed out.") from exc
        if request.status_code >= 400:
            print(request)
            raise HTTPException(status_code=502, detail="Unable to get data from external source")
        return request.json()


class ElasticsearchConnector(DatasetConnector):
    """
    Connector using the Elasticsearch index
    """
    es_index: Index
    dataset: Dataset

    def __init__(self, dataset: Dataset, es_index: Index):
        self.es_index = es_index
        self.dataset = dataset

    def get_item(self, identifier: str):
        item = self.es_index.by_identifier(identifier, self.dataset.detail_id)
        return item.es_result


def get_dataset_connector(dataset: DatasetDep, elastic_index: ElasticIndexDep) -> DatasetConnector:
    """
    Depends on the type
    :param elastic_index:
    :param dataset:
    :return:
    """
    if dataset.data_type == "cmdi":
        return CMDIEditorConnector(dataset, elastic_index)
    if dataset.data_type == "elasticsearch":
        return ElasticsearchConnector(dataset, elastic_index)
    raise HTTPException(status_code=500, detail="Dataset misconfigured")

DatasetConnectorDep = Annotated[DatasetConnector, Depends(get_dataset_connector)]
