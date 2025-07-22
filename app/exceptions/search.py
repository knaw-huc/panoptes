"""
Facets related to search.
"""

from typing import List


class UnknownFacetsException(Exception):
    """
    This error occurs when trying to search using one or more unknown facets.
    """
    facets: List[str]

    def __init__(self, message: str, facets: List[str]):
        super(UnknownFacetsException, self).__init__(message)
        self.facets = facets
