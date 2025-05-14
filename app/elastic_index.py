"""
elastic_index.py
This includes class Index for dealing with Elasticsearch.
Contains methods for finding articles.
"""

import math
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
    def make_matches(search_values):
        """
        Create match queries.
        :param search_values:
        :return:
        """
        must_collection = []
        for item in search_values:
            if item["field"] == "FREE_TEXT":
                for value in item["values"]:
                    must_collection.append({"multi_match": {"query": value, "fields": ["*"]}})
            elif item["field"] in ["year", "lines"]:
                range_values = item["values"][0]
                r_array = range_values.split('-')
                must_collection.append(
                    {"range": {item["field"]: {"gte": r_array[0], "lte": r_array[1]}}}
                )
            else:
                for value in item["values"]:
                    must_collection.append({"match": {item["field"]: value}})
        return must_collection

    def get_facet(self, field: str, amount: int, facet_filter: str, search_values: list):
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


    def browse(self, page, length, search_values):
        """
        Search for articles.
        :param page:
        :param length:
        :param search_values:
        :return:
        """
        int_page = int(page)
        start = (int_page - 1) * length

        if search_values:
            query = {
                "bool": {
                    "must": self.make_matches(search_values)
                }
            }
        else:
            query = {
                "match_all": {}
            }


        response = self.client.search(index=self.index_name, body={
            "query": query,
            "size": length,
            "from": start,
        })

        return {"amount": response["hits"]["total"]["value"],
                "pages": math.ceil(response["hits"]["total"]["value"] / length),
                "items": [item["_source"] for item in response["hits"]["hits"]]}
