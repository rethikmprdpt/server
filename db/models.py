import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from db.base import Base


# Enums
class CustomerStatus(enum.Enum):
    Active = "Active"
    Inactive = "Inactive"
    Pending = "Pending"


class SplitterStatus(enum.Enum):
    operational = "operational"
    faulty = "faulty"
    retired = "retired"


class AssetType(enum.Enum):
    ONT = "ONT"
    Router = "Router"


class AssetStatus(enum.Enum):
    assigned = "assigned"
    available = "available"
    faulty = "faulty"
    retired = "retired"


class BearingStatus(enum.Enum):
    bearing = "bearing"
    returned = "returned"


class PortStatus(enum.Enum):
    free = "free"
    occupied = "occupied"


# Models
class Warehouse(Base):
    __tablename__ = "warehouses"

    warehouse_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    address: Mapped[str] = mapped_column(String(255))
    pincode: Mapped[str] = mapped_column(String(6))

    assets: Mapped[list["Asset"]] = relationship(back_populates="warehouse")


class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(String(255))
    pincode: Mapped[str] = mapped_column(String(10))
    plan: Mapped[str] = mapped_column(String(50))
    status: Mapped[CustomerStatus] = mapped_column(Enum(CustomerStatus))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    ports: Mapped[list["Port"]] = relationship(back_populates="customer")
    assets: Mapped[list["Asset"]] = relationship(back_populates="customer")
    asset_assignments: Mapped[list["AssetAssignment"]] = relationship(
        back_populates="customer",
    )


class FDH(Base):
    __tablename__ = "fdhs"

    fdh_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    model: Mapped[str] = mapped_column(String(50))
    pincode: Mapped[str] = mapped_column(String(10))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 8))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(11, 8))

    splitters: Mapped[list["Splitter"]] = relationship(back_populates="fdh")


class Splitter(Base):
    __tablename__ = "splitters"

    splitter_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    model: Mapped[str] = mapped_column(String(50))
    status: Mapped[SplitterStatus] = mapped_column(Enum(SplitterStatus))
    max_ports: Mapped[int]
    used_ports: Mapped[int] = mapped_column(default=0)
    fdh_id: Mapped[int | None] = mapped_column(ForeignKey("fdhs.fdh_id"))

    fdh: Mapped["FDH"] = relationship(back_populates="splitters")
    ports: Mapped[list["Port"]] = relationship(back_populates="splitter")


class Port(Base):
    __tablename__ = "ports"

    port_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        unique=True,
    )
    port_status: Mapped[PortStatus] = mapped_column(Enum(PortStatus))
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.customer_id"))
    splitter_id: Mapped[int] = mapped_column(ForeignKey("splitters.splitter_id"))

    customer: Mapped[Customer | None] = relationship(back_populates="ports")
    splitter: Mapped["Splitter"] = relationship(back_populates="ports")
    assets: Mapped[list["Asset"]] = relationship(back_populates="port")


class Asset(Base):
    __tablename__ = "assets"

    asset_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type: Mapped[AssetType] = mapped_column(Enum(AssetType))
    model: Mapped[str] = mapped_column(String(50))
    serial_number: Mapped[str] = mapped_column(String(100), unique=True)
    status: Mapped[AssetStatus] = mapped_column(Enum(AssetStatus))
    pincode: Mapped[str] = mapped_column(String(10))
    assigned_to_customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.customer_id"),
    )
    stored_at_warehouse_id: Mapped[int | None] = mapped_column(
        ForeignKey("warehouses.warehouse_id"),
    )
    port_id: Mapped[int | None] = mapped_column(ForeignKey("ports.port_id"))

    customer: Mapped[Customer | None] = relationship(back_populates="assets")
    warehouse: Mapped[Warehouse | None] = relationship(back_populates="assets")
    port: Mapped[Port | None] = relationship(back_populates="assets")
    asset_assignments: Mapped[list["AssetAssignment"]] = relationship(
        back_populates="asset",
    )


class AssetAssignment(Base):
    __tablename__ = "asset_assignments"

    assignment_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.asset_id"))
    bearing_status: Mapped[BearingStatus] = mapped_column(Enum(BearingStatus))
    date_of_issue: Mapped[datetime]
    date_of_return: Mapped[datetime | None]
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.customer_id"))

    asset: Mapped["Asset"] = relationship(back_populates="asset_assignments")
    customer: Mapped["Customer"] = relationship(back_populates="asset_assignments")
