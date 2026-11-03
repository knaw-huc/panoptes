"""
Tests for app.tasks.tree_facets.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models import Dataset
from app.tasks.tree_facets import construct_tree


def make_dataset() -> Dataset:
    """Build a dataset for the tree construction task."""
    return Dataset(
        name="my-dataset",
        es_index="my-index",
        data_type="elasticsearch",
        data_configuration={"id_property": "id", "base_url": "https://example.org"},
        metadata={},
        detail_id="_id",
    )


def make_db(facet_doc):
    """
    Build a fake Mongo database with `facets` and `nodes` collections.
    `db["facets"].find(...).to_list()` resolves to `[facet_doc]`, and
    `db["nodes"]` is a plain MagicMock collection so inserted documents can be
    inspected via `insert_one.call_args_list`.
    """
    facets_collection = MagicMock()
    find_cursor = MagicMock()
    find_cursor.to_list = AsyncMock(return_value=[facet_doc])
    facets_collection.find.return_value = find_cursor

    nodes_collection = MagicMock()

    collections = {"facets": facets_collection, "nodes": nodes_collection}

    db = MagicMock()
    db.__getitem__.side_effect = collections.__getitem__
    return db, nodes_collection


@pytest.mark.asyncio
async def test_construct_tree_inserts_nodes_for_each_tree_entry():
    """Insert both parent and child entries from the facet tree."""
    dataset = make_dataset()
    facet_doc = {"_id": "facet1", "dataset_name": "my-dataset", "property": "path"}
    db, nodes_collection = make_db(facet_doc)

    es_index = MagicMock()
    es_index.get_tree.return_value = [
        {
            "value": "a",
            "name": "a",
            "children": [
                {"value": "a|b", "name": "b", "children": []},
            ],
        }
    ]

    await construct_tree("path", dataset, db, es_index)

    assert nodes_collection.insert_one.call_count == 2
    inserted_values = [call.args[0]["value"] for call in nodes_collection.insert_one.call_args_list]
    assert set(inserted_values) == {"a", "a|b"}
