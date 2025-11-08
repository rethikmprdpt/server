import csv
import io
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

# Import all necessary components
from db.database import get_db
from db.models import User, UserRole
from routers.auth_router import get_current_user
from schemas import audit as audit_schema
from services import audit as audit_service

audit_router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@audit_router.get(
    "/",
    response_model=list[audit_schema.AuditLogRead],
    summary="Get all audit logs with filters",
)
def get_all_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    user_id: Annotated[
        int | None,
        Query(description="Filter logs by a specific user ID."),
    ] = None,
    days_ago: Annotated[
        int | None,
        Query(
            description="Filter logs from the past N days.",
        ),
    ] = None,
):
    # --- Role-Based Security Check ---
    if current_user.role != UserRole.Admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view audit logs.",
        )

    logs = audit_service.get_audit_logs(db=db, user_id=user_id, days_ago=days_ago)
    return logs


@audit_router.get(
    "/export-csv",
    summary="Export filtered audit logs as a CSV file",
    response_class=StreamingResponse,
)
def export_logs_as_csv(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    user_id: Annotated[
        int | None,
        Query(
            description="Filter logs by a specific user ID.",
        ),
    ] = None,
    days_ago: Annotated[
        int | None,
        Query(
            description="Filter logs from the past N days.",
        ),
    ] = None,
):
    # --- Role-Based Security Check ---
    if current_user.role != UserRole.Admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action.",
        )

    # 1. Fetch the filtered data using the exact same service
    logs = audit_service.get_audit_logs(db=db, user_id=user_id, days_ago=days_ago)

    # 2. Create a CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write the header row
    writer.writerow(
        ["Log ID", "Timestamp", "Username", "User ID", "Action", "Description"],
    )

    # Write the data rows
    for log in logs:
        writer.writerow(
            [
                log.log_id,
                log.timestamp.isoformat(),
                log.user.username if log.user else "N/A",
                log.user_id,
                log.action_type.value,
                log.description,
            ],
        )

    # 3. Stream the CSV data back as a file
    response = StreamingResponse(iter([output.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=audit_logs.csv"
    return response
