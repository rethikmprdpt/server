# ruff: noqa: G004
import logging

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from db.models import Asset, AssetAssignment, AssetStatus, AssetType

log = logging.getLogger(__name__)


def get_asset_by_id(db: Session, asset_id: int) -> Asset | None:
    log.info(f"Attempting to fetch asset with id: {asset_id}")
    try:
        asset = db.get(Asset, asset_id)
        if asset:
            log.info(f"Successfully found asset: {asset.serial_number}")
        else:
            log.warning(f"Asset with id {asset_id} not found.")
    except SQLAlchemyError:
        log.exception(f"Database error while fetching asset {asset_id}")
        raise
    else:
        return asset


def get_asset_history_by_asset_id(
    db: Session,
    asset_id: int,
) -> list[AssetAssignment] | None:
    log.info(f"Attempting to fetch asset history for asset_id: {asset_id}")

    try:
        asset = db.get(Asset, asset_id)
        if not asset:
            log.warning(f"Asset with id {asset_id} not found.")
            return None

        stmt = (
            select(AssetAssignment)
            .where(AssetAssignment.asset_id == asset_id)
            .options(selectinload(AssetAssignment.customer))
        )
        history = db.scalars(stmt).all()

        log.info(f"Found {len(history)} history records for asset {asset_id}.")
        return list(history)

    except SQLAlchemyError:
        log.exception(f"Database error while fetching history for asset {asset_id}")
        raise


def get_assets(
    db: Session,
    asset_type: AssetType,
    asset_status: AssetStatus = AssetStatus.available,
) -> list[Asset]:
    # Convert Pydantic enums from the query into the SQLAlchemy model enums
    model_type_enum = AssetType(asset_type.value)
    model_status_enum = AssetStatus(asset_status.value)

    return (
        db.query(Asset)
        .filter(
            Asset.type == model_type_enum,
            Asset.status == model_status_enum,
        )
        .all()
    )
