from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from schemas import inventory as inventory_schema
from services import inventory as inventory_service

inventory_router = APIRouter(prefix="/inventory")


@inventory_router.get(
    "/",
    response_model=inventory_schema.LocationInventory,
)
async def get_assets_by_location(
    db: Annotated[Session, Depends(get_db)],
    pincode: str | None = None,
):
    assets = inventory_service.get_inventory(db=db, pincode=pincode)
    return assets
