"""Shared test data builders."""

from app.models import Dataset


def make_dataset(**overrides) -> Dataset:
    """Build a dataset with defaults that individual tests can override."""
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
