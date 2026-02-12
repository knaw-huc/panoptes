"""
elastic_index.py
This includes class Index for dealing with Elasticsearch.
Contains methods for finding articles.
"""
import math
from typing import List, Dict

from elasticsearch import Elasticsearch

from app.exceptions.search import UnknownFacetsException
from app.models import Facet, FacetType
from app.services.search.dataclasses import FilterOptions, SearchResult, ResultItem


class Index:
    """
    An elasticsearch index of articles.
    """
    client: Elasticsearch
    index_name: str
    facet_configuration: Dict[str, Facet]

    def __init__(self, client: Elasticsearch, index_name: str, available_facets: List[Facet]):
        self.client = client
        self.index_name = index_name
        self.facet_configuration = {
            facet.property: facet
            for facet in available_facets
        }

    @staticmethod
    def no_case(str_in):
        """
        Create query from string, case-insensitive.
        :param str_in:
        :return:
        """
        string = str_in.strip()
        ret_str = ""
        if string != "":
            for char in string:
                ret_str = ret_str + "[" + char.upper() + char.lower() + "]"
        return ret_str + ".*"

    def make_matches(self, filter_options: FilterOptions) -> List:
        """
        Create match queries.
        :param filter_options:
        :return:
        """
        must_collection = []
        unknown_facets = []
        for key, values in filter_options.facets.items():
            if key not in self.facet_configuration:
                unknown_facets.append(key)
                continue
            facet = self.facet_configuration[key]
            if facet.type in [FacetType.RANGE, FacetType.HISTOGRAM]:
                range_values = values[0]
                r_array = range_values.split(':')
                must_collection.append(
                    {"range": {key: {"gte": r_array[0], "lte": r_array[1]}}}
                )
            else:
                must_collection.append({"terms": {key: values}})
        if unknown_facets:
            raise UnknownFacetsException("Unknown facets", unknown_facets)
        if filter_options.query != '':
            must_collection.append(
                {
                    "multi_match": {
                        "query": filter_options.query,
                        "fields": ["*"]
                    }
                }
            )
        return must_collection

    def get_facet(self, facet: Facet, amount: int, facet_filter: str,
                  filter_options: FilterOptions):
        """
        Get the available options for a specific facet, based on a search query. This is used for
        showing the options still relevant given the current search query.
        :param facet:
        :param amount:
        :param facet_filter:
        :param filter_options:
        :return:
        """
        val_key = "key"
        if facet.type == FacetType.HISTOGRAM:
            agg_settings = {
                "field": facet.property,
                "interval": facet.interval,
            }
            agg_type = 'histogram'
        elif facet.type == FacetType.DATE:
            agg_settings = {
                "field": facet.property,
                # "calendar_interval": facet.interval,
                "buckets": 50,
                "format": "yyyy-MM-dd"
            }
            agg_type = 'auto_date_histogram'
            # val_key = "key_as_string"
        else:
            agg_settings = {
                "field": facet.property,
                "size": amount,
                "order": {
                    "_count": "desc"
                }
            }
            agg_type = 'terms'

        if facet_filter:
            filtered_filter = ''.join([f"[{char.upper()}{char.lower()}]" for char in facet_filter])
            agg_settings["include"] = f'.*{filtered_filter}.*'

        body = {
            "size": 0,
            "aggs": {
                "names": {
                    agg_type: agg_settings
                }
            }
        }

        if filter_options.not_empty():
            filter_options.remove_facet(facet.property)
            body["query"] = {
                "bool": {
                    "must": self.make_matches(filter_options)
                }
            }
        response = self.client.search(index=self.index_name, body=body)
        response_data = [{"value": hits[val_key], "count": hits["doc_count"]}
                         for hits in response["aggregations"]["names"]["buckets"]]

        return response_data

    def get_tree(self, facet: Facet, filter_options: FilterOptions):
        """
        Get the tree with all options for a tree facet
        :param facet:
        :param filter_options:
        :return:
        """
        options = self.get_facet(facet, 10000, "",
                                 filter_options)

        tree = {}

        for option in options:
            parts = option["value"].split(facet.tree_separator)
            tmp_tree = tree
            value = {}
            for part in parts:
                if part not in tmp_tree:
                    tmp_tree[part] = {
                        "name": part,
                        "children": {}
                    }
                value = tmp_tree[part]
                tmp_tree = tmp_tree[part]["children"]
            value["value"] = option["value"]
            value["count"] = option["count"]

        def simplify_children(children: Dict) -> List:
            if len(children) == 0:
                return []
            for child in children.values():
                child["children"] = simplify_children(child["children"])
                if "value" not in child:
                    child["count"] = sum(int(c["count"]) for c in child["children"])
            return list(children.values())

        return simplify_children(tree)

    def get_filter_facet(self, field, facet_filter):
        """
        Executes a search query using Elasticsearch to retrieve facet filtering
        results based on the specified field and filter value. It performs an
        aggregation to find terms within the field that match the given filter,
        and sorts the results by document count in descending order. Only terms
        that contain the filter value (case-insensitive) are included in the
        returned list.

        :param field: The field name in the Elasticsearch index to perform the
            aggregation on.
        :type field: str
        :param facet_filter: The filter string to match against the terms in the
            specified field.
        :type facet_filter: str
        :return: A list of dictionaries containing terms from the aggregation
            results. Each dictionary contains a "key" (term name) and
            "doc_count" (the number of documents matching the term).
        :rtype: list[dict]
        """
        ret_array = []
        response = self.client.search(
            index=self.index_name,
            body=
            {
                "query": {
                    "regexp": {
                        field: self.no_case(facet_filter)
                    }
                },
                "size": 0,
                "aggs": {
                    "names": {
                        "terms": {
                            "field": field,
                            "size": 20,
                            "order": {
                                "_count": "desc"
                            }
                        }
                    }
                }
            }
        )
        for hits in response["aggregations"]["names"]["buckets"]:
            buffer = {"key": hits["key"], "doc_count": hits["doc_count"]}
            if facet_filter.lower() in buffer["key"].lower():
                ret_array.append(buffer)
        return ret_array

    def get_min_max(self, fields):
        """
        Get the minimum and maximum value for fields in :fields:
        :param fields: A list of fields to get the min/max for
        :return:
        """
        aggs = {}
        tmp = {}

        for field in fields:
            aggs[f"min-{field}"] = {
                "min": {
                    "field": field,
                },
            }
            aggs[f"max-{field}"] = {
                "max": {
                    "field": field,
                },
            }
            tmp[field] = {}

        response = self.client.search(
            index=self.index_name,
            body={
                "size": 0,
                "aggs": aggs
            }
        )['aggregations']

        for key, value in response.items():
            agg_type, field = key.split('-')
            tmp[field][agg_type] = value['value']

        return tmp

    def browse(self, offset: int, limit: int, filter_options: FilterOptions) -> SearchResult:
        """
        Search for articles.
        :param filter_options:
        :param offset: Pagination offset.
        :param limit: Pagination limit.
        :return:
        """
        if filter_options.not_empty():
            query = {
                "bool": {
                    "must": self.make_matches(filter_options)
                }
            }
        else:
            query = {
                "match_all": {}
            }

        response = self.client.search(index=self.index_name, body={
            "query": query,
            "highlight": {
                "number_of_fragments": 1,
                "fields": {
                    "*": {}
                }
            },
            "sort": [
                {"_score": {"order": "desc"}},
            ],
            "size": limit,
            "from": offset,
        })

        return SearchResult(
            total_results=response['hits']['total']['value'],
            pages=math.ceil(response["hits"]["total"]["value"] / limit),
            items=[
                ResultItem(
                    es_result=item["_source"],
                    highlight=item.get("highlight", {}),
                    index=item["_id"]
                ) for item in response["hits"]["hits"]
            ]
        )

    def by_identifier(self, identifier: str, field: str) -> ResultItem:
        """
        Get a specific record by identifier.
        :param field:
        :param identifier:
        :return:
        """
        response = self.client.search(index=self.index_name, body={
            "query": {
                "bool": {
                    "must": [
                        {
                            "term": {
                                field: identifier
                            }
                        }
                    ]
                }
            },
            "size": 1,
            "from": 0,
        })

        return ResultItem(es_result=response["hits"]["hits"][0]["_source"],
                          index=response["hits"]["hits"][0]["_id"])
