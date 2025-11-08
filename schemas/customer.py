import enum
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from schemas.asset import AssetRead, SplitterRead


class CustomerStatus(str, enum.Enum):
    Active = "Active"
    Inactive = "Inactive"
    Pending = "Pending"


class CustomerBase(BaseModel):
    name: str
    address: str
    pincode: str
    plan: str

    model_config = ConfigDict(from_attributes=True)


class CustomerCreate(CustomerBase):
    splitter_id: int
    ont_asset_id: int
    router_asset_id: int


class CustomerRead(CustomerBase):
    customer_id: int
    status: CustomerStatus
    created_at: datetime


class PortDetailSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    port_id: int
    splitter: SplitterRead | None = None  # Nested Splitter

    # Note: We can get the FDH from the nested splitter
    # but if a port can exist without a splitter, we'd change this.


class CustomerProvisioningDetailsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # We will find the port assigned to the customer
    port: PortDetailSchema | None = None

    # We will find the ONT asset assigned to the customer
    ont_asset: AssetRead | None = None

    # We will find the Router asset assigned to the customer
    router_asset: AssetRead | None = None


class CustomerDeactivationDetailsRead(BaseModel):
    customer: CustomerRead
    provisioning: CustomerProvisioningDetailsRead

    model_config = ConfigDict(from_attributes=True)
