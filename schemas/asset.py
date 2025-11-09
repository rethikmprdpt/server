# from datetime import datetime
# from decimal import Decimal

# from pydantic import BaseModel, ConfigDict

# from db.models import AssetStatus, AssetType, BearingStatus


# class CustomerLite(BaseModel):
#     model_config = ConfigDict(from_attributes=True)
#     customer_id: int
#     name: str


# class PortLite(BaseModel):
#     model_config = ConfigDict(from_attributes=True)
#     port_id: int
#     port_status: str  # You might want to use PortStatus enum here


# class AssetAssignmentLite(BaseModel):
#     model_config = ConfigDict(from_attributes=True)
#     assignment_id: int
#     bearing_status: BearingStatus
#     customer_id: int


# class AssetBase(BaseModel):
#     type: AssetType
#     model: str
#     serial_number: str
#     status: AssetStatus
#     pincode: str
#     assigned_to_customer_id: int | None = None
#     port_id: int | None = None


# class AssetRead(AssetBase):
#     model_config = ConfigDict(from_attributes=True)
#     asset_id: int
#     customer: CustomerLite | None = None
#     port: PortLite | None = None
#     asset_assignments: list[AssetAssignmentLite] = []


# class AssetAssignmentRead(BaseModel):
#     model_config = ConfigDict(from_attributes=True)

#     assignment_id: int
#     asset_id: int
#     bearing_status: BearingStatus
#     date_of_issue: datetime
#     date_of_return: datetime | None = None
#     customer: CustomerLite


# class SplitterLite(BaseModel):
#     model_config = ConfigDict(from_attributes=True)

#     splitter_id: int
#     model: str
#     status: AssetStatus


# class SplitterRead(SplitterLite):
#     max_ports: int
#     used_ports: int
#     fdh_id: int | None


# # --- FDH Schemas ---


# class FdhBase(BaseModel):
#     """Base for an FDH."""

#     model_config = ConfigDict(from_attributes=True)

#     fdh_id: int
#     model: str
#     pincode: str
#     latitude: Decimal | None
#     longitude: Decimal | None


# class FdhRead(FdhBase):
#     pass


# class FdhReadWithSplitters(FdhBase):
#     splitters: list[SplitterLite] = []


import enum
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

# --- NEW: Pydantic Enums for Query Parameters ---
# These are the str, enum.Enum versions
# We'll import the *model* enums for the schemas below
from db.models import (
    AssetStatus as ModelAssetStatus,
)
from db.models import (
    AssetType as ModelAssetType,
)
from db.models import (
    BearingStatus as ModelBearingStatus,
)


class AssetType(str, enum.Enum):
    """Pydantic-compatible AssetType for query params."""

    ONT = "ONT"
    Router = "Router"


class AssetStatus(str, enum.Enum):
    """Pydantic-compatible AssetStatus for query params."""

    assigned = "assigned"
    available = "available"
    faulty = "faulty"
    retired = "retired"


class PortStatus(str, enum.Enum):
    free = "free"
    occupied = "occupied"


# --- YOUR EXISTING SCHEMAS (Unchanged, just using Model enums) ---


class CustomerLite(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    customer_id: int
    name: str


class PortLite(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    port_id: int
    port_status: PortStatus  # You might want to use PortStatus enum here


class PortRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    port_id: int
    port_status: PortStatus
    splitter_id: int
    customer_id: int | None = None


class AssetAssignmentLite(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    assignment_id: int
    bearing_status: ModelBearingStatus
    customer_id: int


class AssetBase(BaseModel):
    type: ModelAssetType
    model: str
    serial_number: str
    status: ModelAssetStatus
    pincode: str
    assigned_to_customer_id: int | None = None
    port_id: int | None = None


class AssetRead(AssetBase):
    model_config = ConfigDict(from_attributes=True)
    asset_id: int
    customer: CustomerLite | None = None
    port: PortLite | None = None
    asset_assignments: list[AssetAssignmentLite] = []


class AssetAssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    assignment_id: int
    asset_id: int
    bearing_status: ModelBearingStatus
    date_of_issue: datetime
    date_of_return: datetime | None = None
    customer: CustomerLite


class SplitterLite(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    splitter_id: int
    model: str
    status: ModelAssetStatus


# --- FDH Schemas ---


class FdhBase(BaseModel):
    """Base for an FDH."""

    model_config = ConfigDict(from_attributes=True)

    fdh_id: int
    model: str
    pincode: str
    latitude: Decimal | None
    longitude: Decimal | None


class FdhRead(FdhBase):
    pass


class FdhReadWithSplitters(FdhBase):
    splitters: list[SplitterLite] = []


class SplitterRead(SplitterLite):
    max_ports: int
    used_ports: int
    fdh: FdhRead | None
