"""
Tests for app.models.
"""

from app.models import Dataset, DataConfiguration, Facet, FacetType, ResultProperty


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


class TestDataset:
    def test_get_config_returns_data_configuration(self):
        dataset = make_dataset()

        config = dataset.get_config()

        assert isinstance(config, DataConfiguration)
        assert config.id_property == "id"
        assert config.base_url == "https://example.org"
        assert config.auth is None

    def test_get_config_with_auth(self):
        dataset = make_dataset(data_configuration={
            "id_property": "id",
            "base_url": "https://example.org",
            "auth": {"username": "user", "password": "pass"},
        })

        config = dataset.get_config()

        assert config.use_auth() is True
        assert config.auth == {"username": "user", "password": "pass"}


class TestDataConfiguration:
    def test_use_auth_false_when_no_auth(self):
        config = DataConfiguration(id_property="id", base_url="https://example.org")

        assert config.use_auth() is False

    def test_use_auth_true_when_auth_present(self):
        config = DataConfiguration(id_property="id", base_url="https://example.org",
                                    auth={"username": "u", "password": "p"})

        assert config.use_auth() is True


class TestFacet:
    def test_type_stored_as_plain_value(self):
        facet = Facet(dataset_name="my-dataset", property="category", name="Category",
                      type=FacetType.TEXT)

        # use_enum_values=True means the stored value is the raw string, not the Enum member.
        assert facet.type == "text"


class TestBaseProperty:
    def test_render_value_returns_first_match(self):
        prop = ResultProperty(dataset_name="my-dataset", name="Title", path="$.title",
                              order=0, type=FacetType.TEXT)

        assert prop.render_value({"title": "Hello world"}) == "Hello world"

    def test_render_value_returns_none_when_no_match(self):
        prop = ResultProperty(dataset_name="my-dataset", name="Title", path="$.title",
                              order=0, type=FacetType.TEXT)

        assert prop.render_value({"other": "value"}) is None

    def test_get_path_returns_path(self):
        prop = ResultProperty(dataset_name="my-dataset", name="Title", path="$.title",
                              order=0, type=FacetType.TEXT)

        assert prop.get_path() == "$.title"
