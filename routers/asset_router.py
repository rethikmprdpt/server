from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# import services.assets as asset_service
from db.database import get_db
from db.models import User, UserRole
from routers.auth_router import get_current_user
from schemas import asset as asset_schema
from services.asset import (
    create_asset,
    create_assets_bulk,
    delete_asset,
    get_asset_by_id,
    get_asset_history_by_asset_id,
    get_assets,
    swap_assets,
    update_asset,
)

asset_router = APIRouter(prefix="/assets")


@asset_router.get(
    "/{asset_id}",
    response_model=asset_schema.AssetRead,
)
async def get_asset_with_id(
    asset_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    # asset = asset_service.get_asset_by_id(db=db, asset_id=asset_id)
    asset = get_asset_by_id(db=db, asset_id=asset_id)
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
    # history = asset_service.get_asset_history_by_asset_id(db=db, asset_id=asset_id)
    history = get_asset_history_by_asset_id(db=db, asset_id=asset_id)
    if not history:
        # Return an empty list instead of 404
        return []
    return history


@asset_router.get(
    "/",
    response_model=list[asset_schema.AssetRead],
    summary="Get assets by type and status",
)
async def get_assets_by_type_and_status(
    db: Annotated[Session, Depends(get_db)],
    asset_type: asset_schema.AssetType,  # Required query param (e.g., "ONT")
    asset_status: asset_schema.AssetStatus = asset_schema.AssetStatus.available,  # Optional
):
    # assets = asset_service.get_assets(
    assets = get_assets(
        db=db,
        asset_type=asset_type,
        asset_status=asset_status,
    )
    return assets


# --- 1. CREATE Endpoint ---
@asset_router.post(
    "/",
    response_model=asset_schema.AssetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new asset (ONT or Router)",
)
def create_new_asset(
    asset_data: asset_schema.AssetCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    # Role Check
    if current_user.role not in [UserRole.Admin, UserRole.Planner]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to add assets.",
        )

    try:
        new_asset = create_asset(
            db=db,
            asset_data=asset_data,
            current_user=current_user,
        )
    except HTTPException as e:
        raise e from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
    else:
        return new_asset


@asset_router.post(
    "/bulk",
    response_model=list[asset_schema.AssetRead],
    status_code=status.HTTP_201_CREATED,
    summary="Bulk create assets (for CSV upload)",
)
def create_assets_bulk_endpoint(
    assets_data: list[asset_schema.AssetCreate],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    # Role Check
    if current_user.role not in [UserRole.Admin, UserRole.Planner]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to add assets.",
        )

    try:
        new_assets = create_assets_bulk(
            db=db,
            assets_data=assets_data,
            current_user=current_user,
        )
    except HTTPException as e:
        raise e from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
    else:
        return new_assets


@asset_router.patch(
    "/{asset_id}",
    response_model=asset_schema.AssetRead,
    summary="Update an existing asset",
)
def update_existing_asset(
    asset_id: int,
    asset_update: asset_schema.AssetUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    # Role Check
    if current_user.role not in [UserRole.Admin, UserRole.Planner]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update assets.",
        )

    try:
        updated_asset = update_asset(
            db=db,
            asset_id=asset_id,
            update_data=asset_update,
            current_user=current_user,
        )
    except HTTPException as e:
        raise e from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
    else:
        return updated_asset


@asset_router.delete(
    "/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an asset",
)
def delete_existing_asset(
    asset_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    # Role Check
    if current_user.role not in [UserRole.Admin, UserRole.Planner]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete assets.",
        )

    try:
        delete_asset(db=db, asset_id=asset_id, current_user=current_user)
    except HTTPException as e:
        raise e from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@asset_router.post(
    "/swap",
    response_model=asset_schema.AssetRead,
    summary="Swap an assigned asset with a new one",
)
def swap_asset_endpoint(
    swap_data: asset_schema.AssetSwap,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.role not in [UserRole.Admin, UserRole.Planner, UserRole.Technician]:
        raise HTTPException(status_code=403, detail="Permission denied.")

    try:
        # We call the service directly (assuming you imported it as asset_service or direct function)
        # Adjust 'asset_service.swap_assets' based on your imports
        return swap_assets(db=db, swap_data=swap_data, current_user=current_user)
    except HTTPException as e:
        raise e from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
