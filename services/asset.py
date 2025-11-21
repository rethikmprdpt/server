from datetime import datetime, timezone  # Ensure these are imported

from fastapi import HTTPException, status
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

# Models & Enums
from db.models import Asset, AssetAssignment, AuditLogActionType, BearingStatus, User
from db.models import AssetStatus as ModelAssetStatus
from db.models import AssetType as ModelAssetType

# Schemas
from schemas import asset as asset_schema

# Audit Service
from services.audit import create_audit_log

# --- READ Operations (Existing + New Helper) ---


def get_assets(
    db: Session,
    asset_type: asset_schema.AssetType,
    asset_status: asset_schema.AssetStatus = asset_schema.AssetStatus.available,
) -> list[Asset]:
    model_type_enum = ModelAssetType(asset_type.value)
    model_status_enum = ModelAssetStatus(asset_status.value)

    return (
        db.query(Asset)
        .filter(Asset.type == model_type_enum, Asset.status == model_status_enum)
        .all()
    )


def get_asset_by_id(db: Session, asset_id: int) -> Asset | None:
    """Gets a single asset by its ID."""
    return db.get(Asset, asset_id)


def get_asset_history_by_asset_id(db: Session, asset_id: int) -> list[AssetAssignment]:
    """Gets the assignment history for a single asset."""
    return (
        db.query(AssetAssignment)
        .filter(AssetAssignment.asset_id == asset_id)
        .order_by(AssetAssignment.date_of_issue.desc())
        .all()
    )


# --- CREATE Operation ---


def create_asset(
    db: Session,
    asset_data: asset_schema.AssetCreate,
    current_user: User,
) -> Asset:
    # 1. Check for duplicate serial number
    existing_asset = (
        db.query(Asset).filter(Asset.serial_number == asset_data.serial_number).first()
    )
    if existing_asset:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Asset with serial number '{asset_data.serial_number}' already exists.",
        )

    try:
        # 2. Create the asset
        new_asset = Asset(
            type=ModelAssetType(asset_data.type.value),
            model=asset_data.model,
            serial_number=asset_data.serial_number,
            pincode=asset_data.pincode,
            status=ModelAssetStatus.available,  # Default to available on creation
        )

        db.add(new_asset)
        db.flush()  # Get ID

        # 3. Audit Log
        create_audit_log(
            db=db,
            user=current_user,
            action_type=AuditLogActionType.CREATE,
            description=f"User '{current_user.username}' created new {new_asset.type.value}: '{new_asset.model}' (SN: {new_asset.serial_number}).",
        )

        # 4. Commit
        db.commit()
        db.refresh(new_asset)

    except Exception as e:
        db.rollback()
        raise e
    else:
        return new_asset


def create_assets_bulk(
    db: Session,
    assets_data: list[asset_schema.AssetCreate],
    current_user: User,
) -> list[Asset]:
    # 1. Pre-validation: Check for duplicates within the CSV itself
    incoming_serials = [a.serial_number for a in assets_data]
    if len(incoming_serials) != len(set(incoming_serials)):
        # Find the duplicates for a helpful error message
        seen = set()
        duplicates = {x for x in incoming_serials if x in seen or seen.add(x)}
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Duplicate serial numbers found within the upload file: {duplicates}",
        )

    # 2. Pre-validation: Check for conflicts in the Database
    # We want to know if ANY of these serials already exist
    existing_assets = (
        db.query(Asset).filter(Asset.serial_number.in_(incoming_serials)).all()
    )

    if existing_assets:
        found_serials = [a.serial_number for a in existing_assets]
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"The following serial numbers already exist in the system: {found_serials}",
        )

    try:
        new_assets = []

        # 3. Create Asset Objects
        for asset_data in assets_data:
            new_asset = Asset(
                type=ModelAssetType(asset_data.type.value),
                model=asset_data.model,
                serial_number=asset_data.serial_number,
                pincode=asset_data.pincode,
                status=ModelAssetStatus(asset_data.status.value),
            )
            db.add(new_asset)
            new_assets.append(new_asset)

        # 4. Flush to assign IDs (but don't commit yet)
        db.flush()

        # 5. Create ONE Summary Audit Log
        # Calculate counts for the log
        ont_count = sum(1 for a in assets_data if a.type.value == "ONT")
        router_count = sum(1 for a in assets_data if a.type.value == "Router")

        create_audit_log(
            db=db,
            user=current_user,
            action_type=AuditLogActionType.CREATE,
            description=f"User '{current_user.username}' bulk imported {len(new_assets)} assets ({ont_count} ONTs, {router_count} Routers).",
        )

        # 6. Commit the Transaction
        db.commit()

        # 7. Refresh instances
        # (Refreshing in a loop can be slow for huge batches, but fine for CSV uploads of ~100s)
        for asset in new_assets:
            db.refresh(asset)

    except Exception as e:
        db.rollback()
        raise e from e
    else:
        return new_assets


# --- UPDATE Operation ---


def update_asset(
    db: Session,
    asset_id: int,
    update_data: asset_schema.AssetUpdate,
    current_user: User,
) -> Asset:
    # 1. Fetch Asset
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")

    # 2. BUSINESS RULE: Cannot edit assigned assets
    if asset.status == ModelAssetStatus.assigned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot edit an asset that is currently assigned to a customer. Please unassign it via the Support Dashboard first.",
        )

    try:
        # 3. Apply updates
        # We only update fields that are provided in the schema
        if update_data.model:
            asset.model = update_data.model
        if update_data.pincode:
            asset.pincode = update_data.pincode

        # Handle Status Change
        # Note: Pydantic ensures this is not None if we made it required
        new_status_enum = ModelAssetStatus(update_data.status.value)

        # Rule: Don't allow setting status to 'assigned' manually via this endpoint
        # Assignment logic is complex and handled by Customer Onboarding.
        if new_status_enum == ModelAssetStatus.assigned:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot manually set status to 'assigned'. Use the Customer Onboarding flow.",
            )

        asset.status = new_status_enum

        # 4. Audit Log
        create_audit_log(
            db=db,
            user=current_user,
            action_type=AuditLogActionType.UPDATE,
            description=f"User '{current_user.username}' updated Asset ID {asset.asset_id}. New Status: {asset.status.value}.",
        )

        # 5. Commit
        db.add(asset)
        db.commit()
        db.refresh(asset)

    except HTTPException as e:
        # Pass through HTTP exceptions (like the rule checks above)
        raise e
    except Exception as e:
        db.rollback()
        raise e
    else:
        return asset


# --- DELETE Operation ---


def delete_asset(db: Session, asset_id: int, current_user: User):
    # 1. Fetch Asset
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")

    # 2. BUSINESS RULE: Cannot delete assigned assets
    if asset.status == ModelAssetStatus.assigned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete an asset that is currently assigned to a customer.",
        )

    try:
        # 3. Audit Log (Must happen before delete, so we can log the serial/model)
        create_audit_log(
            db=db,
            user=current_user,
            action_type=AuditLogActionType.DELETE,
            description=f"User '{current_user.username}' deleted {asset.type.value}: '{asset.model}' (SN: {asset.serial_number}).",
        )

        # 4. Delete
        db.delete(asset)

        # 5. Commit
        db.commit()

    except Exception as e:
        db.rollback()
        raise e


# --- SWAP Operation ---


def swap_assets(db: Session, swap_data: asset_schema.AssetSwap, current_user: User):
    # 1. Fetch both assets
    old_asset = db.get(Asset, swap_data.old_asset_id)
    new_asset = db.get(Asset, swap_data.new_asset_id)

    # 2. Validations
    if not old_asset or not new_asset:
        raise HTTPException(status_code=404, detail="One or both assets not found.")

    if old_asset.status != ModelAssetStatus.assigned:
        raise HTTPException(
            status_code=400,
            detail="Old asset is not currently assigned.",
        )

    if new_asset.status != ModelAssetStatus.available:
        raise HTTPException(status_code=400, detail="New asset is not available.")

    if old_asset.type != new_asset.type:
        raise HTTPException(
            status_code=400,
            detail="Cannot swap assets of different types.",
        )

    try:
        # 3. Capture Context
        customer_id = old_asset.assigned_to_customer_id
        port_id = old_asset.port_id

        # 4. Close History for Old Asset
        # Find the open assignment record
        old_assignment = (
            db.query(AssetAssignment)
            .filter(
                AssetAssignment.asset_id == old_asset.asset_id,
                AssetAssignment.date_of_return is None,
            )
            .first()
        )

        if old_assignment:
            old_assignment.date_of_return = datetime.now(timezone.utc)
            old_assignment.bearing_status = BearingStatus.returned
            db.add(old_assignment)

        # 5. Update Old Asset (Make it available)
        old_asset.status = ModelAssetStatus.available
        old_asset.assigned_to_customer_id = None
        old_asset.port_id = None
        db.add(old_asset)

        # 6. Update New Asset (Assign it)
        new_asset.status = ModelAssetStatus.assigned
        new_asset.assigned_to_customer_id = customer_id
        new_asset.port_id = port_id  # Transfer port connection if it exists
        db.add(new_asset)

        # 7. Create New History Log
        new_assignment = AssetAssignment(
            asset_id=new_asset.asset_id,
            customer_id=customer_id,
            bearing_status=BearingStatus.bearing,
            date_of_issue=datetime.now(timezone.utc),
        )
        db.add(new_assignment)

        # 8. Audit Log
        create_audit_log(
            db=db,
            user=current_user,
            action_type=AuditLogActionType.UPDATE,
            description=f"User '{current_user.username}' swapped {old_asset.type.value}: '{old_asset.serial_number}' -> '{new_asset.serial_number}' for Customer ID {customer_id}.",
        )

        db.commit()

    except Exception as e:
        db.rollback()
        raise e from e
    else:
        return new_asset
