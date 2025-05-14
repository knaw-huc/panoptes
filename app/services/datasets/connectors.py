"""
Implementation specific classes for dealing with dataset connections.
"""

from abc import ABC, abstractmethod
from typing import Dict

import requests
from fastapi import HTTPException


class DatasetConnector(ABC):
    """
    Base class for all datasets connectors.
    """
    @abstractmethod
    def __init__(self, configuration: Dict[str, str]) -> None:
        """
        Initialize a dataset connector instance. Always has a configuration dictionary as argument.
        Implementation is dataset type dependent.
        :param configuration:
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

    def __init__(self, configuration: Dict[str, str]) -> None:
        self.api_base = configuration["base_url"]


    def get_item(self, identifier: str):
        request = requests.get(f"{self.api_base}/{identifier}", headers={
            "Accept": "application/json"
        })
        if request.status_code != 200:
            print(request)
            raise HTTPException(status_code=502, detail="Unable to get data from external source")
        return request.json()
