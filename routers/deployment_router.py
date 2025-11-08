from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import User
from routers.auth_router import get_current_user
from schemas import deployment_task as deployment_task_schema
from services import deployment_task as deployment_task_service

deployment_router = APIRouter(prefix="/deployment-tasks", tags=["Deployment Tasks"])


@deployment_router.post(
    "/",
    response_model=deployment_task_schema.DeploymentTaskRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new deployment task (Assign a technician)",
)
def create_deployment_task(
    task: deployment_task_schema.DeploymentTaskCreate,
    db: Annotated[Session, Depends(get_db)],
):
    try:
        # The service function will do all the heavy lifting
        new_task = deployment_task_service.create_deployment_task(db=db, task=task)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create task: {e!s}",
        )
    else:
        return new_task


@deployment_router.get(
    "/",
    response_model=list[deployment_task_schema.DeploymentTaskRead],
    summary="Get deployment tasks by status",
)
def get_deployment_tasks_by_status(
    status: Annotated[
        deployment_task_schema.DeploymentTaskStatus,
        Query(
            ...,
            description="Filter tasks by their status (e.g., Scheduled, InProgress)",
        ),
    ],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    tasks = deployment_task_service.get_tasks_by_status(
        db=db,
        status=status,
        user=current_user,
    )
    return tasks


@deployment_router.patch(
    "/{task_id}",
    response_model=deployment_task_schema.DeploymentTaskRead,
    summary="Update a task's checklist",
)
def update_task_checklist_endpoint(
    task_id: int,
    checklist_data: deployment_task_schema.DeploymentTaskChecklistUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        updated_task = deployment_task_service.update_task_checklist(
            db=db,
            task_id=task_id,
            checklist=checklist_data,
            current_user=current_user,
        )
    except HTTPException as e:
        raise e  # noqa: TRY201
    except Exception as e:  # noqa: BLE001
        # Catch any unexpected errors
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    else:
        return updated_task
