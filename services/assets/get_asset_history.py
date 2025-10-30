# ruff: noqa: G004
import logging

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from db.models import Asset, AssetAssignment

log = logging.getLogger(__name__)


def get_asset_history_by_asset_id(
    db: Session,
    asset_id: int,
) -> list[AssetAssignment] | None:
    log.info(f"Attempting to fetch asset history for asset_id: {asset_id}")

    try:
        # First, check if the asset exists
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
