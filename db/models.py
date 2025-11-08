import enum
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from db.base import Base


# Enums
class CustomerStatus(enum.Enum):
    Active = "Active"
    Inactive = "Inactive"
    Pending = "Pending"


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


class UserRole(enum.Enum):
    Planner = "Planner"
    Technician = "Technician"
    Admin = "Admin"
    SupportAgent = "SupportAgent"


class DeploymentTaskStatus(enum.Enum):
    Scheduled = "Scheduled"
    InProgress = "InProgress"
    Completed = "Completed"
    Failed = "Failed"


class AuditLogActionType(enum.Enum):
    READ = "READ"
    UPDATE = "UPDATE"
    CREATE = "CREATE"
    DELETE = "DELETE"


# Models


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
    deployment_tasks: Mapped[list["DeploymentTask"]] = relationship(
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
    status: Mapped[AssetStatus] = mapped_column(Enum(AssetStatus))
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
    port_id: Mapped[int | None] = mapped_column(ForeignKey("ports.port_id"))

    customer: Mapped[Customer | None] = relationship(back_populates="assets")
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


class User(Base):
    __tablename__ = "users"
    user_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    deployment_tasks: Mapped[list["DeploymentTask"]] = relationship(
        back_populates="user",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="user",
    )


class DeploymentTask(Base):
    __tablename__ = "deployment_tasks"

    task_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.customer_id"))
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"),
    )

    status: Mapped[DeploymentTaskStatus] = mapped_column(
        Enum(DeploymentTaskStatus),
        default=DeploymentTaskStatus.Scheduled,
    )
    scheduled_date: Mapped[datetime] = mapped_column(
        DateTime,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- NEW CHECKLIST COLUMNS ---
    step_1: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="0",
        nullable=False,
    )
    step_2: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="0",
        nullable=False,
    )
    step_3: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="0",
        nullable=False,
    )
    # --- END OF NEW COLUMNS ---

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )

    # --- Relationships ---
    customer: Mapped["Customer"] = relationship(back_populates="deployment_tasks")
    user: Mapped["User"] = relationship(back_populates="deployment_tasks")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    log_id: Mapped[int] = mapped_column(primary_key=True)
    action_type: Mapped[AuditLogActionType] = mapped_column(
        Enum(AuditLogActionType),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=timezone.utc),
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id"),
        nullable=True,
    )

    user: Mapped["User"] = relationship("User", back_populates="audit_logs")
