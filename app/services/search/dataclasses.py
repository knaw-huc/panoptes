"""
dataclasses.py
Data classes for dealing with the search services.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

import jsonpath

from app.models import BaseProperty


@dataclass
class ResultItem:
    """
    A search result item
    """
    es_result: Dict
    index: str
    highlight: Optional[Dict] = None


    def format_highlight(self) -> str:
        """
        Format the highlight into a single string
        :return:
        """
        return "<br />".join(["<br />".join(items) for items in self.highlight.values()])


    def format_result(self, properties: List[BaseProperty]) -> Dict:
        """
        Formats a single result into a dict with only the required fields.
        :param properties:
        :return:
        """
        tmp_result = {
            **self.es_result,
            '_id': self.index,
            '_highlight': self.format_highlight(),
        }
        return {
            prop.name: jsonpath.findall(prop.path, tmp_result)[0] for prop in properties
                if len(jsonpath.findall(prop.path, tmp_result))
        }

    def get_prop(self, name: str):
        """
        Get property
        :param name:
        :return:
        """
        return self.index if name == "_id" else self.es_result.get(name)

@dataclass
class FilterOptions:
    """
    Options for filtering in a dataset
    """
    facets: Dict[str, List[str]]
    query: str = ""

    def not_empty(self):
        """
        Check if filtering should be performed.
        :return:
        """
        return bool(self.facets) or self.query != ""

    def remove_facet(self, name: str):
        """
        Removes a facet from the filter.
        :param name:
        :return:
        """
        self.facets.pop(name, None)


@dataclass
class SearchResult:
    """
    Search results
    """
    total_results: int
    pages: int
    items: List[ResultItem]

    def format_results(self, properties: List[BaseProperty]) -> List[Dict]:
        """
        Processes the ES results into dicts with only the required properties.
        """
        return [item.format_result(properties) for item in self.items]
