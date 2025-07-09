"""
elastic_index.py
This includes class Index for dealing with Elasticsearch.
Contains methods for finding articles.
"""

import math
from typing import List

from elasticsearch import Elasticsearch

from app.services.search.dataclasses import FilterOptions, SearchResult, ResultItem


class Index:
    """
    An elasticsearch index of articles.
    """
    client: Elasticsearch
    index_name: str

    def __init__(self, client: Elasticsearch, index_name: str):
        self.client = client
        self.index_name = index_name

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

    @staticmethod
    def make_matches(filter_options: FilterOptions) -> List:
        """
        Create match queries.
        :param filter_options:
        :return:
        """
        must_collection = []
        for key, values in filter_options.facets.items():
            if key in ["year", "lines"]:
                range_values = values[0]
                r_array = range_values.split('-')
                must_collection.append(
                    {"range": {key: {"gte": r_array[0], "lte": r_array[1]}}}
                )
            else:
                must_collection.append({"terms": {key: values}})
        if filter_options.query != '':
            must_collection.append(
                {"multi_match": {"query": filter_options.query, "fields": ["*"]}}
            )
        return must_collection


    def get_facet(self, field: str, amount: int, facet_filter: str, filter_options: FilterOptions):
        """
        Get the available options for a specific facet, based on a search query. This is used for
        showing the options still relevant given the current search query.
        :param field:
        :param amount:
        :param facet_filter:
        :param filter_options:
        :return:
        """
        terms = {
            "field": field,
            "size": amount,
            "order": {
                "_count": "desc"
            }
        }

        if facet_filter:
            filtered_filter = ''.join([f"[{char.upper()}{char.lower()}]" for char in facet_filter])
            terms["include"] = f'.*{filtered_filter}.*'

        body = {
            "size": 0,
            "aggs": {
                "names": {
                    "terms": terms
                }
            }
        }

        if filter_options.not_empty():
            body["query"] = {
                "bool": {
                    "must": self.make_matches(filter_options)
                }
            }
        response = self.client.search(index=self.index_name, body=body)

        return [{"value": hits["key"], "count": hits["doc_count"]}
                for hits in response["aggregations"]["names"]["buckets"]]


    def get_filter_facet(self, field, facet_filter):
        """
        Get a filter facet.
        :param field:
        :param facet_filter:
        :return:
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


    def get_nested_facet(self, field, amount):
        """
        Get a nested facet.
        :param field:
        :param amount:
        :return:
        """
        ret_array = []
        path = field.split('.')[0]
        response = self.client.search(
            index=self.index_name,
            body=
            {
                "size": 0,
                "aggs": {
                    "nested_terms": {
                        "nested": {
                            "path": path
                        },
                        "aggs": {
                            "filter": {
                                "filter": {
                                    "regexp": {
                                        "$field.raw": "$filter.*"
                                    }
                                },
                                "aggs": {
                                    "names": {
                                        "terms": {
                                            "field": "$field.raw",
                                            "size": amount
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        )
        for hits in response["aggregations"]["nested_terms"]["filter"]["names"]["buckets"]:
            buffer = {"key": hits["key"], "doc_count": hits["doc_count"]}
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

        print("query:", query)

        response = self.client.search(index=self.index_name, body={
            "query": query,
            "size": limit,
            "from": offset,
        })

        return SearchResult(
            total_results=response['hits']['total']['value'],
            pages=math.ceil(response["hits"]["total"]["value"] / limit),
            items=[
                ResultItem(
                    es_result=item["_source"],
                    index=item["_id"]
                ) for item in response["hits"]["hits"]
            ]
        )
