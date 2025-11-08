from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.database import get_db
from schemas.asset import FdhRead, SplitterRead
from services import fdh as fdh_service

fdh_router = APIRouter(prefix="/fdhs", tags=["FDHs (Fiber Distribution Hubs)"])


@fdh_router.get("/", response_model=list[FdhRead], summary="Get all FDHs")
def get_fdhs(db: Annotated[Session, Depends(get_db)]):
    return fdh_service.get_all_fdhs(db=db)


@fdh_router.get(
    "/{fdh_id}/splitters",
    response_model=list[SplitterRead],
    summary="Get splitters for a specific FDH",
)
def get_splitters_for_fdh(
    fdh_id: int,
    db: Annotated[Session, Depends(get_db)],
    open_ports_only: Annotated[  # noqa: FBT002
        bool,
        Query(
            alias="openPortsOnly",  # This allows the frontend to call ?openPortsOnly=true
            description="If true, only return splitters with at least one free port.",
        ),
    ] = False,
):
    # We can add a check here to see if FDH exists first, but for now
    # just getting the splitters is fine.
    splitters = fdh_service.get_splitters_by_fdh_id(
        db=db,
        fdh_id=fdh_id,
        open_ports_only=open_ports_only,
    )

    # Return an empty list, not a 404, if no splitters are found
    return splitters
