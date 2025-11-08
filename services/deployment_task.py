from fastapi import HTTPException, status  # noqa: INP001
from sqlalchemy.orm import Session, joinedload

from db.models import (  # We need this to check if the user exists
    Customer,
    CustomerStatus,
    DeploymentTask,
    DeploymentTaskStatus,
    User,
    UserRole,
)
from schemas import deployment_task as deployment_task_schema


# Custom exceptions are a good practice for cleaner router handling
class CustomerNotFoundError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


def create_deployment_task(
    db: Session,
    task: deployment_task_schema.DeploymentTaskCreate,
) -> DeploymentTask:
    # 1. Get the customer
    db_customer = (
        db.query(Customer).filter(Customer.customer_id == task.customer_id).first()
    )

    if not db_customer:
        msg = f"Customer with id {task.customer_id} not found."
        raise CustomerNotFoundError(
            msg,
        )

    # Optional: Check if customer is actually pending
    if db_customer.status != CustomerStatus.Pending:
        msg = f"Customer is not in 'Pending' state. Current state: {db_customer.status.value}"
        raise Exception(  # noqa: TRY002
            msg,
        )

    # 2. Get the user (technician)
    db_user = db.query(User).filter(User.user_id == task.user_id).first()

    if not db_user:
        msg = f"User (Technician) with id {task.user_id} not found."
        raise UserNotFoundError(
            msg,
        )

    # 3. Update the customer's status
    # They are no longer pending, they are now an active customer
    # being scheduled for deployment.

    # 4. Create the new DeploymentTask
    # The status will default to 'Scheduled' based on our model definition
    new_task = DeploymentTask(
        customer_id=task.customer_id,
        user_id=task.user_id,
        scheduled_date=task.scheduled_date,
        notes=task.notes,
    )

    try:
        db.add(new_task)
        db.commit()
        db.refresh(new_task)

        # Eagerly load the relationships for the response model
        db.query(DeploymentTask).filter(
            DeploymentTask.task_id == new_task.task_id,
        ).options(
            joinedload(DeploymentTask.customer),
            joinedload(DeploymentTask.user),
        ).first()

        return new_task  # noqa: TRY300
    except Exception as e:
        db.rollback()
        raise e  # noqa: TRY201


def get_tasks_by_status(
    db: Session,
    status: deployment_task_schema.DeploymentTaskStatus,
    user: User,  # --- ACCEPT THE USER OBJECT ---
) -> list[DeploymentTask]:
    # Convert Pydantic enum from query to the DB Model enum
    model_status = DeploymentTaskStatus(status.value)

    # 1. Start building the base query
    query = (
        db.query(DeploymentTask)
        .options(
            joinedload(DeploymentTask.customer),
            joinedload(DeploymentTask.user),
        )
        .filter(DeploymentTask.status == model_status)
    )

    # --- 2. THIS IS THE SECURITY LOGIC ---
    # If the user is a technician, add a filter for their user_id
    if user.role == UserRole.Technician:
        query = query.filter(DeploymentTask.user_id == user.user_id)

    return query.all()


def update_task_checklist(
    db: Session,
    task_id: int,
    checklist: deployment_task_schema.DeploymentTaskChecklistUpdate,
    current_user: User,
) -> DeploymentTask:
    # 1. Find the task
    task = db.get(DeploymentTask, task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    # 2. Check permissions
    if (
        current_user.role == UserRole.Technician
        and task.user_id != current_user.user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this task.",
        )
    # Planners and Admins can update any task

    # 3. Apply the updates
    task.step_1 = checklist.step_1
    task.step_2 = checklist.step_2
    task.step_3 = checklist.step_3

    # 4. Check if the task is now completed
    # 4. Check if the task is now completed
    if task.step_1 and task.step_2 and task.step_3:  # noqa: SIM102
        # This code ONLY runs if all 3 steps are True
        if task.status != DeploymentTaskStatus.Completed:
            task.status = DeploymentTaskStatus.Completed

            # This is the logic you want:
            if task.customer:
                task.customer.status = CustomerStatus.Active
                db.add(task.customer)

    # 5. Commit, refresh, and return
    db.add(task)
    db.commit()
    db.refresh(task)

    return task
