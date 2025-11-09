from fastapi import HTTPException, status  # noqa: INP001
from sqlalchemy.orm import Session, joinedload

from db.models import (  # We need this to check if the user exists
    AuditLogActionType,
    Customer,
    CustomerStatus,
    DeploymentTask,
    DeploymentTaskStatus,
    User,
    UserRole,
)
from schemas import deployment_task as deployment_task_schema
from services.audit import create_audit_log


# Custom exceptions are a good practice for cleaner router handling
class CustomerNotFoundError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


def create_deployment_task(
    db: Session,
    task: deployment_task_schema.DeploymentTaskCreate,
    current_user: User,
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
        # 5. Add the new task to the session
        db.add(new_task)

        # 6. Flush (but don't commit) to get the new_task.task_id
        db.flush()

        # 7. Create the audit log *before* committing
        create_audit_log(
            db=db,
            user=current_user,  # This is the Planner/Admin who clicked "Assign"
            action_type=AuditLogActionType.CREATE,
            description=f"User '{current_user.username}' created Task (ID: {new_task.task_id}) for Customer '{db_customer.name}', assigned to Technician '{current_user.username}'.",
        )

        # 8. Commit the transaction (saves both the task and the log)
        db.commit()

        # 9. Now, query for the full object to return
        # This is the correct way to load relationships for the response
        complete_task = (
            db.query(DeploymentTask)
            .options(
                joinedload(DeploymentTask.customer),
                joinedload(DeploymentTask.user),
            )
            .filter(DeploymentTask.task_id == new_task.task_id)
            .first()
        )

        if not complete_task:
            # This should never happen, but it's good practice
            raise HTTPException(  # noqa: TRY301
                status_code=404,
                detail="Task created but could not be retrieved.",
            )

    except Exception as e:
        db.rollback()
        # Re-raise the exception to be caught by the router
        raise e  # noqa: TRY201
    else:
        return complete_task


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

    create_audit_log(
        db=db,
        user=user,
        action_type=AuditLogActionType.READ,
        description=f"User '{user.username}' viewed task list for status '{status.value}'.",
    )
    db.commit()

    return query.all()


# def update_task_checklist(
#     db: Session,
#     task_id: int,
#     checklist: deployment_task_schema.DeploymentTaskChecklistUpdate,
#     current_user: User,
# ) -> DeploymentTask:
#     # 1. Find the task
#     task = db.get(DeploymentTask, task_id)

#     if not task:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Task not found",
#         )

#     # 2. Check permissions
#     if (
#         current_user.role == UserRole.Technician
#         and task.user_id != current_user.user_id
#     ):
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="You are not authorized to update this task.",
#         )
#     # Planners and Admins can update any task

#     # 3. Apply the updates
#     task.step_1 = checklist.step_1
#     task.step_2 = checklist.step_2
#     task.step_3 = checklist.step_3

#     # 4. Check if the task is now completed
#     # 4. Check if the task is now completed
#     if task.step_1 and task.step_2 and task.step_3:  # noqa: SIM102
#         # This code ONLY runs if all 3 steps are True
#         if task.status != DeploymentTaskStatus.Completed:
#             task.status = DeploymentTaskStatus.Completed

#             # This is the logic you want:
#             if task.customer:
#                 task.customer.status = CustomerStatus.Active
#                 db.add(task.customer)

#     # 5. Commit, refresh, and return
#     db.add(task)
#     create_audit_log(
#         db=db,
#         user=current_user,
#         action_type=AuditLogActionType.UPDATE,
#         description=f"User {current_user.username} changed task status of task_id: {task_id}",
#     )

#     # ... (your db.add(task), db.add(customer), etc.) ...
#     db.commit()
#     db.refresh(task)

#     return task


def update_task_checklist(
    db: Session,
    task_id: int,
    checklist: deployment_task_schema.DeploymentTaskChecklistUpdate,
    current_user: User,
) -> DeploymentTask:
    # 1. Find the task AND its related customer in one query
    task = (
        db.query(DeploymentTask)
        .options(joinedload(DeploymentTask.customer))
        .filter(DeploymentTask.task_id == task_id)
        .first()
    )

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

    # --- 3. (NEW) Prevent updates on finalized tasks ---
    if task.status in [DeploymentTaskStatus.Completed, DeploymentTaskStatus.Failed]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task is already {task.status.value} and cannot be modified.",
        )

    # 4. Apply the updates
    task.step_1 = checklist.step_1
    task.step_2 = checklist.step_2
    task.step_3 = checklist.step_3

    # --- 5. (NEW) Automatically update status based on checklist ---

    # Store old status for logging
    old_status = task.status

    if task.step_1 and task.step_2 and task.step_3:
        # All 3 are checked: Mark as Completed
        task.status = DeploymentTaskStatus.Completed
        if task.customer:
            task.customer.status = CustomerStatus.Active
            db.add(task.customer)  # Add the customer to the session for update

    elif task.step_1 or task.step_2 or task.step_3:
        # At least 1 (but not all 3) is checked: Mark as InProgress
        task.status = DeploymentTaskStatus.InProgress

    else:
        # All 0 are checked: Revert to Scheduled
        task.status = DeploymentTaskStatus.Scheduled

    # --- 6. Create Audit Log ---
    log_desc = f"User '{current_user.username}' updated checklist for Task (ID: {task.task_id}). Steps: [1: {task.step_1}, 2: {task.step_2}, 3: {task.step_3}]."

    # Add more detail if the status changed
    if old_status != task.status:
        log_desc += (
            f" Task status changed from '{old_status.value}' to '{task.status.value}'."
        )
        if task.status == DeploymentTaskStatus.Completed:
            log_desc += " Customer status set to 'Active'."

    create_audit_log(
        db=db,
        user=current_user,
        action_type=AuditLogActionType.UPDATE,
        description=log_desc,
    )

    # 7. Commit, refresh, and return
    db.add(task)
    db.commit()

    # We need to refresh the relationships as well
    db.refresh(task)
    if task.customer:
        db.refresh(task.customer)

    # Re-load the 'user' relationship which wasn't part of this query
    task_user = db.get(User, task.user_id)
    task.user = task_user

    return task
