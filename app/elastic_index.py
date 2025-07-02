"""
elastic_index.py
This includes class Index for dealing with Elasticsearch.
Contains methods for finding articles.
"""

import math
from typing import Dict, List

from elasticsearch import Elasticsearch


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
    def make_matches(search_values: Dict[str, List[str]], query: str = '') -> List:
        """
        Create match queries.
        :param search_values:
        :param query:
        :return:
        """
        must_collection = []
        for key, values in search_values.items():
            if key in ["year", "lines"]:
                # TODO: make this depend on facet type
                range_values = values[0]
                r_array = range_values.split('-')
                must_collection.append(
                    {"range": {key: {"gte": r_array[0], "lte": r_array[1]}}}
                )
            else:
                must_collection.append({"terms": {key: values}})
        if query != '':
            must_collection.append({"multi_match": {"query": query, "fields": ["*"]}})
        return must_collection


    def get_facet(self, field: str, amount: int, facet_filter: str, search_values: Dict[str, List]):
        """
        Get a facet.
        :param field:
        :param amount:
        :param facet_filter:
        :param search_values:
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

        if search_values:
            body["query"] = {
                "bool": {
                    "must": self.make_matches(search_values)
                }
            }
        response = self.client.search(index=self.index_name, body=body)

        return [{"key": hits["key"], "doc_count": hits["doc_count"]}
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


    def browse(self, offset: int, limit: int, search_values: Dict[str, List[str]], query: str = ''):
        """
        Search for articles.
        :param offset: Pagination offset.
        :param limit: Pagination limit.
        :param search_values: Dictionary of facets to filter on
        :param query: Query for text-based search.
        :return:
        """
        if search_values:
            query = {
                "bool": {
                    "must": self.make_matches(search_values, query)
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

        return {"amount": response["hits"]["total"]["value"],
                "pages": math.ceil(response["hits"]["total"]["value"] / limit),
                "items": [item["_source"] for item in response["hits"]["hits"]]}
