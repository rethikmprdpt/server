from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import services.assets as asset_service
from db.database import get_db
from schemas import asset as asset_schema

asset_router = APIRouter(prefix="/assets")


# @asset_router.post(
#     "/",
#     response_model=asset_schema.AssetRead,
#     status_code=status.HTTP_201_CREATED,
# )
# async def create_new_asset(
#     asset_in: asset_schema.AssetCreate,
#     db: Annotated[AsyncSession, Depends(get_db)],
# ):
#     new_asset = await asset_service.create_asset(db=db, asset_in=asset_in)
#     if not new_asset:
#         raise HTTPException(
#             status_code=400,
#             detail="Failed to create asset. Serial number already exists.",
#         )
#     return new_asset


@asset_router.get(
    "/",
    response_model=list[asset_schema.AssetRead],
)
async def get_assets_by_location(
    pincode: str,
    db: Annotated[Session, Depends(get_db)],
):
    assets = asset_service.get_assets_by_pincode(db=db, pincode=pincode)
    # An empty list is a valid response, no 404 needed.
    return assets


@asset_router.get(
    "/{asset_id}",
    response_model=asset_schema.AssetRead,
)
async def get_asset_by_id(
    asset_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    asset = asset_service.get_asset_by_id(db=db, asset_id=asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@asset_router.get(
    "/{asset_id}/history",
    response_model=list[asset_schema.AssetAssignmentRead],
)
async def get_asset_assignment_history(
    asset_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    history = asset_service.get_asset_history_by_asset_id(db=db, asset_id=asset_id)
    if not history:
        # Return an empty list instead of 404
        return []
    return history


# @asset_router.put(
#     "/{asset_id}",
#     response_model=asset_schema.AssetRead,
# )
# async def update_asset(
#     asset_id: int,
#     asset_update: asset_schema.AssetUpdate,
#     db: Annotated[AsyncSession, Depends(get_db)],
# ):
#     updated_asset = await asset_service.update_asset(
#         db=db,
#         asset_id=asset_id,
#         asset_update=asset_update,
#     )
#     if not updated_asset:
#         raise HTTPException(status_code=404, detail="Asset not found")
#     return updated_asset
