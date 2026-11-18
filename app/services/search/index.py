"""
Base class for search index implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List

from app.models import Facet
from app.services.search.dataclasses import FilterOptions, ResultItem, SearchResult


class Index(ABC):
    """
    Abstract base class for an index.
    """

    @abstractmethod
    def get_fields(self) -> List[str]:
        """Return all fields available in the index."""

    @abstractmethod
    def make_matches(self, filter_options: FilterOptions) -> List:
        """Build query clauses from the supplied filters."""

    @abstractmethod
    def get_facet(self, facet: Facet, amount: int, facet_filter: str,
                  filter_options: FilterOptions, sort: str = "hits") -> List[dict]:
        """Return available values for a facet."""

    @abstractmethod
    def get_tree(self, facet: Facet, filter_options: FilterOptions) -> List[dict]:
        """Return the hierarchical values for a tree facet."""

    @abstractmethod
    def get_filter_facet(self, field: str, facet_filter: str) -> List[dict]:
        """Return facet values matching the supplied filter."""

    @abstractmethod
    def get_min_max(self, fields: List[str]) -> Dict[str, Dict]:
        """Return minimum and maximum values for the supplied fields."""

    @abstractmethod
    def browse(self, offset: int, limit: int, filter_options: FilterOptions) -> SearchResult:
        """Search the index and return a page of results."""

    @abstractmethod
    def by_identifier(self, identifier: str, field: str) -> ResultItem:
        """Return the item matching the identifier."""
