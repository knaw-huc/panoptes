"""
Tests for app.services.search.elastic_index.
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from dateutil.relativedelta import relativedelta

from app.exceptions.search import UnknownFacetsException
from app.models import Facet, FacetType
from app.services.search.dataclasses import FilterOptions
from app.services.search.elastic_index import Index, parse_interval


def make_facet(**overrides) -> Facet:
    defaults = {
        "dataset_name": "my-dataset",
        "property": "category",
        "name": "Category",
        "type": FacetType.TEXT,
    }
    defaults.update(overrides)
    return Facet(**defaults)


def make_index(client=None, facets=None, highlight_fields=None) -> Index:
    return Index(client or MagicMock(), "my-index", facets or [], highlight_fields)


class TestParseInterval:
    @pytest.mark.parametrize("interval_str, expected", [
        ("5y", relativedelta(years=5)),
        ("10m", relativedelta(minutes=10)),
        ("6M", relativedelta(months=6)),
        ("3d", relativedelta(days=3)),
        ("2h", relativedelta(hours=2)),
        ("30s", relativedelta(seconds=30)),
    ])
    def test_parses_valid_intervals(self, interval_str, expected):
        assert parse_interval(interval_str) == expected

    def test_raises_on_invalid_format(self):
        with pytest.raises(ValueError, match="Invalid format"):
            parse_interval("not-an-interval")

    def test_raises_on_unsupported_unit(self):
        with pytest.raises(ValueError, match="Unsupported unit"):
            parse_interval("5x")


class TestNoCase:
    def test_empty_string_returns_wildcard_only(self):
        assert Index.no_case("") == ".*"

    def test_builds_case_insensitive_character_classes(self):
        assert Index.no_case("ab") == "[Aa][Bb].*"

    def test_strips_whitespace(self):
        assert Index.no_case("  a ") == "[Aa].*"


class TestGetFieldsRecursive:
    def test_flat_mapping(self):
        mapping = {
            "title": {"type": "text"},
            "views": {"type": "integer"},
        }

        fields = Index.get_fields_recursive(mapping)

        assert sorted(fields) == ["title", "views"]

    def test_nested_object_properties(self):
        mapping = {
            "author": {
                "properties": {
                    "name": {"type": "text"},
                }
            }
        }

        fields = Index.get_fields_recursive(mapping)

        assert fields == ["author.name"]

    def test_multi_fields(self):
        mapping = {
            "title": {
                "type": "text",
                "fields": {
                    "keyword": {"type": "keyword"},
                },
            }
        }

        fields = Index.get_fields_recursive(mapping)

        assert fields == ["title", "title.keyword"]

    def test_object_type_without_properties_is_skipped(self):
        mapping = {
            "metadata": {"type": "object"},
        }

        fields = Index.get_fields_recursive(mapping)

        assert not fields


class TestMakeMatches:
    def test_terms_match_for_text_facet(self):
        index = make_index(facets=[make_facet(property="category", type=FacetType.TEXT)])
        options = FilterOptions(facets={"category": ["books"]})

        matches = index.make_matches(options)

        assert matches == [{"terms": {"category": ["books"]}}]

    def test_range_match_for_range_facet(self):
        index = make_index(facets=[make_facet(property="price", type=FacetType.RANGE)])
        options = FilterOptions(facets={"price": ["10:20"]})

        matches = index.make_matches(options)

        assert matches == [{"range": {"price": {"gte": "10", "lte": "20"}}}]

    def test_query_string_added_when_query_present(self):
        index = make_index()
        options = FilterOptions(facets={}, query="hello world")

        matches = index.make_matches(options)

        assert matches == [{
            "simple_query_string": {"query": "hello world", "fields": ["*"]}
        }]

    def test_unknown_facet_raises(self):
        index = make_index(facets=[])
        options = FilterOptions(facets={"unknown": ["x"]})

        with pytest.raises(UnknownFacetsException) as exc_info:
            index.make_matches(options)

        assert exc_info.value.facets == ["unknown"]


class TestGetFacet:
    def test_terms_aggregation_returns_value_and_count(self):
        client = MagicMock()
        client.search.return_value = {
            "aggregations": {
                "names": {
                    "buckets": [
                        {"key": "books", "doc_count": 5},
                        {"key": "music", "doc_count": 2},
                    ]
                }
            }
        }
        index = make_index(client=client, facets=[make_facet(type=FacetType.TEXT)])
        facet = make_facet(type=FacetType.TEXT)

        result = index.get_facet(facet, 10, "", FilterOptions(facets={}))

        assert result == [
            {"value": "books", "count": 5},
            {"value": "music", "count": 2},
        ]

    def test_histogram_aggregation_adds_start_and_end(self):
        client = MagicMock()
        client.search.return_value = {
            "aggregations": {
                "names": {
                    "buckets": [
                        {"key": 0, "doc_count": 3},
                    ]
                }
            }
        }
        facet = make_facet(property="score", type=FacetType.HISTOGRAM, interval=10)
        index = make_index(client=client, facets=[facet])

        result = index.get_facet(facet, 10, "", FilterOptions(facets={}))

        assert result == [{"value": 0, "start": 0, "end": 10, "count": 3}]

    def test_query_added_when_filter_options_not_empty(self):
        client = MagicMock()
        client.search.return_value = {"aggregations": {"names": {"buckets": []}}}
        facet = make_facet(property="category", type=FacetType.TEXT)
        other_facet = make_facet(property="other", type=FacetType.TEXT)
        index = make_index(client=client, facets=[facet, other_facet])
        options = FilterOptions(facets={"category": ["books"], "other": ["x"]})

        index.get_facet(facet, 10, "", options)

        _, kwargs = client.search.call_args
        assert "query" in kwargs["body"]
        # The current facet itself should be removed from the filter options used to query.
        assert options.facets == {"other": ["x"]}


class TestGetTree:
    def test_builds_nested_tree_from_separated_values(self):
        client = MagicMock()
        client.search.return_value = {
            "aggregations": {
                "names": {
                    "buckets": [
                        {"key": "a|b", "doc_count": 3},
                        {"key": "a|c", "doc_count": 2},
                    ]
                }
            }
        }
        facet = make_facet(property="path", type=FacetType.TREE, tree_separator="|")
        index = make_index(client=client, facets=[facet])

        tree = index.get_tree(facet, FilterOptions(facets={}))

        assert len(tree) == 1
        root = tree[0]
        assert root["name"] == "a"
        assert root["count"] == 5
        assert {child["value"] for child in root["children"]} == {"a|b", "a|c"}


class TestBrowse:
    def test_match_all_when_no_filters(self):
        client = MagicMock()
        client.search.return_value = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {"_source": {"title": "foo"}, "_id": "abc", "highlight": {}},
                ],
            }
        }
        index = make_index(client=client)

        result = index.browse(0, 10, FilterOptions(facets={}))

        assert result.total_results == 1
        assert result.pages == 1
        assert result.items[0].es_result == {"title": "foo"}
        _, kwargs = client.search.call_args
        assert kwargs["body"]["query"] == {"match_all": {}}

    def test_uses_bool_must_query_when_filters_present(self):
        client = MagicMock()
        client.search.return_value = {
            "hits": {"total": {"value": 0}, "hits": []},
        }
        facet = make_facet(property="category", type=FacetType.TEXT)
        index = make_index(client=client, facets=[facet])

        index.browse(0, 10, FilterOptions(facets={"category": ["books"]}))

        _, kwargs = client.search.call_args
        assert kwargs["body"]["query"] == {
            "bool": {"must": [{"terms": {"category": ["books"]}}]}
        }


class TestByIdentifier:
    def test_returns_result_item_for_first_hit(self):
        client = MagicMock()
        client.search.return_value = {
            "hits": {"hits": [{"_source": {"title": "foo"}, "_id": "abc123"}]}
        }
        index = make_index(client=client)

        item = index.by_identifier("abc123", "_id")

        assert item.es_result == {"title": "foo"}
        assert item.index == "abc123"
