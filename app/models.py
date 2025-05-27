"""
Data models for use with the database.
"""

from typing import Optional, Annotated, Dict

from pydantic import BaseModel, BeforeValidator, Field

# Represents an ObjectId field in the database.
# It will be represented as a `str` on the model so that it can be serialized to JSON.
PyObjectId = Annotated[str, BeforeValidator(str)]

class Tenant(BaseModel):
    """
    Represents an tenant.
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: str
    domain: str


class Dataset(BaseModel):
    """
    Represents a dataset belonging to a tenant
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    tenant_name: str
    name: str
    es_index: str
    data_type: str
    data_configuration: Dict[str, str]


class Facet(BaseModel):
    """
    Represents an indexed facet
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    dataset_id: PyObjectId
    property: str # Name of the field in the ES index
    name: str # Readable name
    type: str


class DetailProperty(BaseModel):
    """
    Represents a property to show in the detail view.
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    dataset_id: PyObjectId
    name: str
    type: str
    path: str # jmespath to the location of the value in the original data
