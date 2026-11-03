"""
Tests for app.services.datasets.connectors.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests
from fastapi import HTTPException

from app.models import Dataset
from app.services.datasets.connectors import (
    CMDIEditorConnector,
    ElasticsearchConnector,
    get_dataset_connector,
)
from app.services.search.dataclasses import ResultItem


def make_dataset(**overrides) -> Dataset:
    defaults = {
        "name": "my-dataset",
        "es_index": "my-index",
        "data_type": "elasticsearch",
        "data_configuration": {"id_property": "id", "base_url": "https://example.org"},
        "metadata": {},
        "detail_id": "_id",
    }
    defaults.update(overrides)
    return Dataset(**defaults)


class TestGetDatasetConnector:
    def test_returns_cmdi_connector_for_cmdi_type(self):
        dataset = make_dataset(data_type="cmdi")
        es_index = MagicMock()

        connector = get_dataset_connector(dataset, es_index)

        assert isinstance(connector, CMDIEditorConnector)

    def test_returns_elasticsearch_connector_for_elasticsearch_type(self):
        dataset = make_dataset(data_type="elasticsearch")
        es_index = MagicMock()

        connector = get_dataset_connector(dataset, es_index)

        assert isinstance(connector, ElasticsearchConnector)

    def test_raises_for_unknown_type(self):
        dataset = make_dataset(data_type="unknown")
        es_index = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            get_dataset_connector(dataset, es_index)

        assert exc_info.value.status_code == 500


class TestElasticsearchConnector:
    def test_get_item_returns_es_result(self):
        es_index = MagicMock()
        es_index.by_identifier.return_value = ResultItem(es_result={"title": "foo"}, index="abc")
        dataset = make_dataset()
        connector = ElasticsearchConnector(dataset, es_index)

        result = connector.get_item("abc")

        assert result == {"title": "foo"}
        es_index.by_identifier.assert_called_once_with("abc", dataset.detail_id)


class TestCMDIEditorConnector:
    def test_get_item_fetches_from_api(self):
        es_index = MagicMock()
        es_index.by_identifier.return_value = ResultItem(es_result={"id": "123"}, index="abc")
        dataset = make_dataset(data_type="cmdi", detail_id="id",
                               data_configuration={"id_property": "id",
                                                   "base_url": "https://example.org/api"})
        connector = CMDIEditorConnector(dataset, es_index)

        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"full": "record"}

        with patch("requests.get", return_value=response) as mock_get:
            result = connector.get_item("abc")

        assert result == {"full": "record"}
        mock_get.assert_called_once()
        assert mock_get.call_args.args[0] == "https://example.org/api/123.json2"

    def test_get_item_adds_basic_auth_header_when_configured(self):
        es_index = MagicMock()
        es_index.by_identifier.return_value = ResultItem(es_result={"id": "123"}, index="abc")
        dataset = make_dataset(data_type="cmdi", detail_id="id",
                               data_configuration={
                                   "id_property": "id",
                                   "base_url": "https://example.org/api",
                                   "auth": {"username": "user", "password": "pass"},
                               })
        connector = CMDIEditorConnector(dataset, es_index)

        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {}

        with patch("requests.get", return_value=response) as mock_get:
            connector.get_item("abc")

        headers = mock_get.call_args.kwargs["headers"]
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")

    def test_get_item_raises_504_on_timeout(self):
        es_index = MagicMock()
        es_index.by_identifier.return_value = ResultItem(es_result={"id": "123"}, index="abc")
        dataset = make_dataset(data_type="cmdi", detail_id="id",
                               data_configuration={"id_property": "id",
                                                   "base_url": "https://example.org/api"})
        connector = CMDIEditorConnector(dataset, es_index)

        with patch("requests.get", side_effect=requests.exceptions.Timeout):
            with pytest.raises(HTTPException) as exc_info:
                connector.get_item("abc")

        assert exc_info.value.status_code == 504

    def test_get_item_raises_502_on_error_response(self):
        es_index = MagicMock()
        es_index.by_identifier.return_value = ResultItem(es_result={"id": "123"}, index="abc")
        dataset = make_dataset(data_type="cmdi", detail_id="id",
                               data_configuration={"id_property": "id",
                                                   "base_url": "https://example.org/api"})
        connector = CMDIEditorConnector(dataset, es_index)

        response = MagicMock()
        response.status_code = 404
        response.json.return_value = {"error": "not found"}

        with patch("requests.get", return_value=response):
            with pytest.raises(HTTPException) as exc_info:
                connector.get_item("abc")

        assert exc_info.value.status_code == 502
