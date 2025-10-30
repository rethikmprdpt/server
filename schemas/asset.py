from datetime import datetime

from pydantic import BaseModel, ConfigDict

from db.models import AssetStatus, AssetType, BearingStatus

# --- Schemas for Related Models ---
# These are "Lite" versions of your other models,
# used to prevent circular imports and to define
# what data is returned *within* the AssetRead model.


class CustomerLite(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    customer_id: int
    name: str


class WarehouseLite(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    warehouse_id: int
    address: str


class PortLite(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    port_id: int
    port_status: str  # You might want to use PortStatus enum here


class AssetAssignmentLite(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    assignment_id: int
    bearing_status: BearingStatus
    customer_id: int


# --- Main Asset Schemas ---


class AssetBase(BaseModel):
    type: AssetType
    model: str
    serial_number: str
    status: AssetStatus
    pincode: str
    assigned_to_customer_id: int | None = None
    stored_at_warehouse_id: int | None = None
    port_id: int | None = None


class AssetRead(AssetBase):
    model_config = ConfigDict(from_attributes=True)
    asset_id: int
    customer: CustomerLite | None = None
    warehouse: WarehouseLite | None = None
    port: PortLite | None = None
    asset_assignments: list[AssetAssignmentLite] = []


class AssetAssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    assignment_id: int
    asset_id: int
    bearing_status: BearingStatus
    date_of_issue: datetime
    date_of_return: datetime | None = None
    customer: CustomerLite  # Include full customer details
