"""
Implementation specific classes for dealing with dataset connections.
"""
import base64
import ipaddress
import socket
from abc import ABC, abstractmethod
from typing import Annotated
from urllib.parse import urlparse

import requests
from fastapi import HTTPException, Depends

from app.dependencies import DatasetDep, SearchIndexDep
from app.models import Dataset, DataConfiguration
from app.services.search.index import Index


def _assert_safe_external_url(url: str) -> None:
    """
    Guard against SSRF: only allow http(s) URLs that do not resolve to
    private, loopback, link-local or otherwise reserved network ranges.
    :param url: the URL to validate
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise HTTPException(status_code=400, detail="Invalid external source URL")

    try:
        addr_infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to resolve external source host",
        ) from exc

    for *_rest, sockaddr in addr_infos:
        ip = ipaddress.ip_address(sockaddr[0])
        if any((
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_reserved,
            ip.is_multicast,
            ip.is_unspecified,
        )):
            raise HTTPException(status_code=400, detail="External source host is not allowed")


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
    search_index: Index
    data_configuration: DataConfiguration

    def __init__(self, dataset: Dataset, search_index: Index) -> None:
        self.dataset = dataset
        self.data_configuration = dataset.get_config()
        self.api_base = self.data_configuration.base_url
        self.id_property = self.data_configuration.id_property
        self.search_index = search_index


    def get_item(self, identifier: str):
        item = self.search_index.by_identifier(identifier, self.dataset.detail_id)
        item_id = item.get_prop(self.id_property)

        try:
            headers = {
                "Accept": "application/json",
            }
            if self.data_configuration.use_auth():
                # For now, auth is always http basic auth
                username = self.data_configuration.auth["username"]
                password = self.data_configuration.auth["password"]
                token = base64.b64encode(f"{username}:{password}".encode('utf-8')).decode("ascii")
                headers["Authorization"] = f"Basic {token}"
            request_url = f"{self.api_base}/{item_id}.json2"
            _assert_safe_external_url(request_url)
            print("Getting " + f"{self.api_base}/{item_id}")
            response = requests.get(request_url, headers=headers, timeout=5, allow_redirects=False)
        except requests.exceptions.Timeout as exc:
            raise HTTPException(status_code=504, detail="External source timed out.") from exc
        if response.status_code >= 400:
            print(response)
            print(response.json())
            raise HTTPException(status_code=502, detail="Unable to get data from external source")
        return response.json()


class SearchIndexConnector(DatasetConnector):
    """
    Connector using the Elasticsearch index
    """
    search_index: Index
    dataset: Dataset

    def __init__(self, dataset: Dataset, search_index: Index):
        self.search_index = search_index
        self.dataset = dataset

    def get_item(self, identifier: str):
        """
        Retrieves an item from the Elasticsearch index using the given identifier.

        :param identifier: A string representing the unique identifier of the item to
            be retrieved.
        :return: The Elasticsearch result corresponding to the provided identifier.
        """
        item = self.search_index.by_identifier(identifier, self.dataset.detail_id)
        return item.es_result


def get_dataset_connector(dataset: DatasetDep, search_index: SearchIndexDep) -> DatasetConnector:
    """
    Depends on the type
    :param search_index:
    :param dataset:
    :return:
    """
    if dataset.data_type == "cmdi":
        return CMDIEditorConnector(dataset, search_index)
    if dataset.data_type == "elasticsearch":
        return SearchIndexConnector(dataset, search_index)
    raise HTTPException(status_code=500, detail="Dataset misconfigured")

DatasetConnectorDep = Annotated[DatasetConnector, Depends(get_dataset_connector)]
