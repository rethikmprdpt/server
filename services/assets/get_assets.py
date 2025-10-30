# ruff: noqa: G004
import logging

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from db.models import Asset

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


def get_assets_by_pincode(db: Session, pincode: str) -> list[Asset]:
    log.info(f"Attempting to fetch assets for pincode: {pincode}")

    try:
        stmt = select(Asset).where(Asset.pincode == pincode)
        assets = db.scalars(stmt).all()

        log.info(f"Found {len(assets)} assets for pincode {pincode}.")
        return list(assets)

    except SQLAlchemyError:
        log.exception(f"Database error while fetching assets for pincode {pincode}")
        raise
