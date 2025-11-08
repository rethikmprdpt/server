from sqlalchemy.orm import Session  # noqa: INP001

from db.models import FDH, Splitter


def get_all_fdhs(db: Session) -> list[FDH]:
    return db.query(FDH).all()


def get_splitters_by_fdh_id(
    db: Session,
    fdh_id: int,
    open_ports_only: bool = False,  # <-- 1. ADDED THIS PARAMETER
) -> list[Splitter]:
    query = db.query(Splitter).filter(Splitter.fdh_id == fdh_id)

    # If the flag is set, add the filter for available ports
    if open_ports_only:
        query = query.filter(Splitter.used_ports < Splitter.max_ports)

    # Execute the query
    return query.all()
