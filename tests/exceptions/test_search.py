"""
Tests for app.exceptions.search.
"""

from app.exceptions.search import UnknownFacetsException


def test_unknown_facets_exception_stores_message_and_facets():
    """Preserve the error message and unknown facet names on the exception."""
    exc = UnknownFacetsException("Unknown facets", ["foo", "bar"])

    assert str(exc) == "Unknown facets"
    assert exc.facets == ["foo", "bar"]
