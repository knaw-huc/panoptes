"""
Tests for app.models.
"""

from app.models import DataConfiguration, Facet, FacetType, ResultProperty
from tests import make_dataset


class TestDataset:
    """Dataset configuration conversion."""

    def test_get_config_returns_data_configuration(self):
        """Convert the stored configuration with no authentication by default."""
        dataset = make_dataset()

        config = dataset.get_config()

        assert isinstance(config, DataConfiguration)
        assert config.id_property == "id"
        assert config.base_url == "https://example.org"
        assert config.auth is None

    def test_get_config_with_auth(self):
        """Preserve authentication credentials in the converted configuration."""
        dataset = make_dataset(data_configuration={
            "id_property": "id",
            "base_url": "https://example.org",
            "auth": {"username": "user", "password": "pass"},
        })

        config = dataset.get_config()

        assert config.use_auth() is True
        assert config.auth == {"username": "user", "password": "pass"}


class TestDataConfiguration:
    """Authentication availability in data configurations."""

    def test_use_auth_false_when_no_auth(self):
        """Report authentication as unavailable when credentials are absent."""
        config = DataConfiguration(id_property="id", base_url="https://example.org")

        assert config.use_auth() is False

    def test_use_auth_true_when_auth_present(self):
        """Report authentication as available when credentials are present."""
        config = DataConfiguration(id_property="id", base_url="https://example.org",
                                    auth={"username": "u", "password": "p"})

        assert config.use_auth() is True


class TestFacet:
    """Facet model serialization."""

    def test_type_stored_as_plain_value(self):
        """Store the facet type as its string value rather than an enum."""
        facet = Facet(dataset_name="my-dataset", property="category", name="Category",
                      type=FacetType.TEXT)

        # use_enum_values=True means the stored value is the raw string, not the Enum member.
        assert facet.type == "text"


class TestBaseProperty:
    """Property value extraction and path access."""

    def test_render_value_returns_first_match(self):
        """Render the first matching value from the configured JSON path."""
        prop = ResultProperty(dataset_name="my-dataset", name="Title", path="$.title",
                              order=0, type=FacetType.TEXT)

        assert prop.render_value({"title": "Hello world"}) == "Hello world"

    def test_render_value_returns_none_when_no_match(self):
        """Return no value when the configured JSON path has no match."""
        prop = ResultProperty(dataset_name="my-dataset", name="Title", path="$.title",
                              order=0, type=FacetType.TEXT)

        assert prop.render_value({"other": "value"}) is None

    def test_get_path_returns_path(self):
        """Return the configured JSON path unchanged."""
        prop = ResultProperty(dataset_name="my-dataset", name="Title", path="$.title",
                              order=0, type=FacetType.TEXT)

        assert prop.get_path() == "$.title"
