import logging

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from db.models import FDH, Asset, Splitter
from schemas import asset as asset_schema
from schemas import inventory as inventory_schema

log = logging.getLogger(__name__)


def get_inventory(
    db: Session,
    pincode: str | None = None,
) -> inventory_schema.LocationInventory:
    if pincode:
        msg = f"Fetching full inventory for pincode: {pincode}"
    else:
        msg = "Fetching all inventory"

    log.info(msg)

    try:
        # 1. Get Assets (ONTs/Routers)
        asset_stmt = select(Asset)
        if pincode:
            asset_stmt = asset_stmt.where(Asset.pincode == pincode)
        assets = list(db.scalars(asset_stmt).all())

        # 2. Get FDHs
        fdh_stmt = select(FDH)
        if pincode:
            fdh_stmt = fdh_stmt.where(FDH.pincode == pincode)
        fdhs = list(db.scalars(fdh_stmt).all())

        # 3. Get Splitters
        splitter_stmt = select(Splitter)
        if pincode:
            # Only join to filter if a pincode is provided
            splitter_stmt = splitter_stmt.join(FDH).where(FDH.pincode == pincode)
        splitters = list(db.scalars(splitter_stmt).all())

        msg = f"Found: {len(assets)} assets, {len(fdhs)} FDHs, {len(splitters)} splitters."
        log.info(msg)

        assets_schemas = [
            asset_schema.AssetRead.model_validate(asset) for asset in assets
        ]
        fdhs_schemas = [asset_schema.FdhRead.model_validate(fdh) for fdh in fdhs]
        splitters_schemas = [
            asset_schema.SplitterRead.model_validate(splitter) for splitter in splitters
        ]

        # 4. Assemble the final response object
        # Use "all" if no pincode was specified, otherwise use the pincode
        report_pincode = pincode if pincode else "all"

        inventory_report = inventory_schema.LocationInventory(
            pincode=report_pincode,
            assets=assets_schemas,
            fdhs=fdhs_schemas,
            splitters=splitters_schemas,
        )

    except SQLAlchemyError:
        msg = f"Database error fetching inventory (pincode: {pincode})"
        log.exception(msg)
        raise
    else:
        return inventory_report
