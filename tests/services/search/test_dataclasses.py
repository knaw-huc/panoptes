"""
Tests for app.services.search.dataclasses.
"""

from app.models import FacetType, ResultProperty
from app.services.search.dataclasses import FilterOptions, ResultItem, SearchResult


def make_property(name, path) -> ResultProperty:
    """Create a text result property with the given name and JSON path."""
    return ResultProperty(dataset_name="my-dataset", name=name, path=path, order=0,
                          type=FacetType.TEXT)


class TestResultItem:
    """Test result field access and property formatting."""

    def test_get_prop_returns_index_for_id(self):
        """Resolve the special identifier property to the item index."""
        item = ResultItem(es_result={"title": "foo"}, index="abc123")

        assert item.get_prop("_id") == "abc123"

    def test_get_prop_returns_field_value(self):
        """Return a field value from the Elasticsearch source."""
        item = ResultItem(es_result={"title": "foo"}, index="abc123")

        assert item.get_prop("title") == "foo"

    def test_get_prop_returns_none_for_missing_field(self):
        """Return None when the requested source field is absent."""
        item = ResultItem(es_result={"title": "foo"}, index="abc123")

        assert item.get_prop("missing") is None

    def test_format_result_includes_only_matched_properties(self):
        """Exclude properties whose JSON paths match no source fields."""
        item = ResultItem(es_result={"title": "foo", "author": "bar"}, index="abc123")
        properties = [make_property("Title", "$.title"), make_property("Missing", "$.missing")]

        result = item.format_result(properties)

        assert result == {"Title": "foo"}

    def test_format_result_can_access_id_and_highlight(self):
        """Expose identifier and highlight metadata during formatting."""
        item = ResultItem(es_result={"title": "foo"}, index="abc123",
                          highlight={"title": ["<em>foo</em>"]})
        properties = [make_property("Id", "$._id"), make_property("Highlight", "$._highlight")]

        result = item.format_result(properties)

        assert result == {"Id": "abc123", "Highlight": {"title": ["<em>foo</em>"]}}


class TestFilterOptions:
    """Test filter presence checks and facet removal."""

    def test_not_empty_false_when_no_facets_or_query(self):
        """Treat options without facets or a query as empty."""
        options = FilterOptions(facets={})

        assert options.not_empty() is False

    def test_not_empty_true_with_facets(self):
        """Treat options containing a facet filter as nonempty."""
        options = FilterOptions(facets={"category": ["books"]})

        assert options.not_empty() is True

    def test_not_empty_true_with_query(self):
        """Treat options containing a query as nonempty."""
        options = FilterOptions(facets={}, query="hello")

        assert options.not_empty() is True

    def test_remove_facet_removes_existing_key(self):
        """Remove the selected facet while preserving other filters."""
        options = FilterOptions(facets={"category": ["books"], "author": ["jane"]})

        options.remove_facet("category")

        assert options.facets == {"author": ["jane"]}

    def test_remove_facet_ignores_missing_key(self):
        """Leave filters unchanged when removing an absent facet."""
        options = FilterOptions(facets={"category": ["books"]})

        options.remove_facet("missing")

        assert options.facets == {"category": ["books"]}


class TestSearchResult:
    """Test formatting of search result collections."""

    def test_format_results_delegates_to_items(self):
        """Format each result item using the supplied properties."""
        item = ResultItem(es_result={"title": "foo"}, index="abc123")
        result = SearchResult(total_results=1, pages=1, items=[item])
        properties = [make_property("Title", "$.title")]

        assert result.format_results(properties) == [{"Title": "foo"}]

    def test_format_results_empty_items(self):
        """Return an empty list when there are no result items."""
        result = SearchResult(total_results=0, pages=0, items=[])

        assert result.format_results([]) == []
