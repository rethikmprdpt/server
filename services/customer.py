from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

# Import all the models and enums we'll need for this transaction
from db.models import (
    Asset,
    AssetAssignment,
    AssetStatus,
    AssetType,
    AuditLogActionType,
    BearingStatus,
    Customer,
    CustomerStatus,
    DeploymentTask,
    Port,
    PortStatus,
    Splitter,
    User,
)
from schemas import customer as customer_schema
from services.audit import create_audit_log


def create_customer(
    db: Session,
    customer: customer_schema.CustomerCreate,
    current_user: User,
) -> Customer:
    # We will manually control the transaction
    try:
        # ... (Steps 1-4: Find port, splitter, ONT, router - all stay the same) ...
        # --- 1. Find the first available port for the chosen splitter ---
        port_to_assign = db.execute(
            select(Port)
            .where(
                Port.splitter_id == customer.splitter_id,
                Port.port_status == PortStatus.free,
            )
            .order_by(Port.port_id)
            .limit(1),
        ).scalar_one_or_none()

        if not port_to_assign:
            raise HTTPException(  # noqa: TRY301
                status_code=status.HTTP_409_CONFLICT,
                detail=f"No free ports available for splitter ID {customer.splitter_id}. Please select another.",
            )

        # --- 2. Find the selected Splitter to update its count ---
        splitter_to_update = db.get(Splitter, customer.splitter_id)
        if not splitter_to_update:
            raise HTTPException(  # noqa: TRY301
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Splitter not found.",
            )

        # --- 3. Find the selected ONT Asset ---
        ont_asset = db.get(Asset, customer.ont_asset_id)
        if not (
            ont_asset
            and ont_asset.status == AssetStatus.available
            and ont_asset.type == AssetType.ONT
        ):
            raise HTTPException(  # noqa: TRY301
                status_code=status.HTTP_409_CONFLICT,
                detail=f"ONT Asset (ID: {customer.ont_asset_id}) is not available or is not an ONT.",
            )

        # --- 4. Find the selected Router Asset ---
        router_asset = db.get(Asset, customer.router_asset_id)
        if not (
            router_asset
            and router_asset.status == AssetStatus.available
            and router_asset.type == AssetType.Router
        ):
            raise HTTPException(  # noqa: TRY301
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Router Asset (ID: {customer.router_asset_id}) is not available or is not a Router.",
            )

        # --- 5. Create the Customer ---
        new_customer = Customer(
            name=customer.name,
            address=customer.address,
            pincode=customer.pincode,
            plan=customer.plan,
            status=CustomerStatus.Pending,  # Default status on creation
        )
        db.add(new_customer)
        db.flush()

        # --- 6. All checks passed. Now, apply all updates ---
        # a) Assign the Port
        port_to_assign.port_status = PortStatus.occupied
        port_to_assign.customer_id = new_customer.customer_id

        # b) Update the Splitter count
        splitter_to_update.used_ports += 1

        # c) Assign the ONT Asset (and link it to the port)
        ont_asset.status = AssetStatus.assigned
        ont_asset.assigned_to_customer_id = new_customer.customer_id
        ont_asset.port_id = port_to_assign.port_id

        # d) Assign the Router Asset
        router_asset.status = AssetStatus.assigned
        router_asset.assigned_to_customer_id = new_customer.customer_id

        # --- 7. (NEW) Create the historical assignment logs ---

        # Get the current time
        issue_date = datetime.now(timezone.utc)

        # Create ONT assignment log
        ont_assignment = AssetAssignment(
            asset_id=ont_asset.asset_id,
            bearing_status=BearingStatus.bearing,
            date_of_issue=issue_date,
            customer_id=new_customer.customer_id,
        )

        # Create Router assignment log
        router_assignment = AssetAssignment(
            asset_id=router_asset.asset_id,
            bearing_status=BearingStatus.bearing,
            date_of_issue=issue_date,
            customer_id=new_customer.customer_id,
        )

        # --- 8. Add ALL changes to the session ---
        db.add_all(
            [
                port_to_assign,
                splitter_to_update,
                ont_asset,
                router_asset,
                ont_assignment,  # <-- NEW
                router_assignment,  # <-- NEW
            ],
        )

        # --- 9. Commit the Transaction ---
        create_audit_log(
            db=db,
            user=current_user,
            action_type=AuditLogActionType.CREATE,
            description=f"User '{current_user.username}' created and provisioned customer '{new_customer.name}' (ID: {new_customer.customer_id}).",
        )
        db.commit()

        # --- 10. Refresh and return the new customer ---
        db.refresh(new_customer)

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:  # noqa: BLE001
        db.rollback()
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred during customer provisioning.",
        )
    else:
        return new_customer


def get_customers_by_status(
    db: Session,
    status: customer_schema.CustomerStatus,
    current_user: User,
) -> list[Customer]:
    # Convert Pydantic enum to SQLAlchemy model enum
    model_status = CustomerStatus[status.value]

    # Start the base query
    query = db.query(Customer).filter(Customer.status == model_status)

    # --- THIS IS THE FIX ---
    if model_status == CustomerStatus.Pending:
        # We only want to show 'Pending' customers who do NOT have a task.
        # This filter translates to:
        # "WHERE NOT EXISTS (SELECT 1 FROM deployment_tasks WHERE deployment_tasks.customer_id = customers.customer_id)"
        query = query.filter(~Customer.deployment_tasks.any())

    # Sort by creation date for consistency
    query = query.order_by(Customer.created_at.desc())

    create_audit_log(
        db=db,
        user=current_user,
        action_type=AuditLogActionType.READ,
        description=f"User '{current_user.username}' fetched customers.",
    )
    db.commit()  # Commit the log

    return query.all()


def get_customer_provisioning_details(
    db: Session,
    customer_id: int,
    current_user: User,
) -> customer_schema.CustomerProvisioningDetailsRead:
    # 1. Define the complex query to get all data at once.
    # This query will join Customer -> Port -> Splitter -> FDH
    # It will also join Customer -> Assets
    customer = (
        db.query(Customer)
        .options(
            joinedload(Customer.ports).options(
                joinedload(Port.splitter).options(joinedload(Splitter.fdh)),
            ),
            joinedload(Customer.assets),
        )
        .filter(Customer.customer_id == customer_id)
        .first()
    )

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    # 2. Process the results in Python

    # Find the assigned port (should be one, but we take the first)
    assigned_port = next(
        (p for p in customer.ports if p.port_status == PortStatus.occupied),
        None,
    )

    # Find the assigned assets
    ont_asset = next(
        (
            a
            for a in customer.assets
            if a.type == AssetType.ONT and a.status == AssetStatus.assigned
        ),
        None,
    )
    router_asset = next(
        (
            a
            for a in customer.assets
            if a.type == AssetType.Router and a.status == AssetStatus.assigned
        ),
        None,
    )

    # 3. Build the Pydantic response schema

    # Manually construct the port details to match PortDetailSchema
    port_details = None
    if assigned_port:
        port_details = customer_schema.PortDetailSchema(
            port_id=assigned_port.port_id,
            splitter=assigned_port.splitter,  # This will be populated due to joinedload
        )

    # Construct the final response
    provisioning_details = customer_schema.CustomerProvisioningDetailsRead(
        port=port_details,
        ont_asset=ont_asset,
        router_asset=router_asset,
    )
    create_audit_log(
        db=db,
        user=current_user,
        action_type=AuditLogActionType.READ,
        description=f"User '{current_user.username}' viewed provisioning details for customer ID {customer_id}.",
    )
    db.commit()

    return provisioning_details


def deactivate_customer_and_provisioning(  # noqa: C901, PLR0915
    db: Session,
    customer_id: int,
    current_user: User,
) -> Customer:
    try:
        # --- 1. Get all related data in one efficient query ---
        customer = (
            db.query(Customer)
            .options(
                joinedload(Customer.ports),
                joinedload(Customer.assets),
                joinedload(Customer.asset_assignments),
            )
            .filter(Customer.customer_id == customer_id)
            .first()
        )

        if not customer:
            raise HTTPException(  # noqa: TRY301
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found.",
            )

        if customer.status == CustomerStatus.Inactive:
            # Customer is already inactive, nothing to do.
            return customer

        # --- 2. Find the specific items to de-provision ---

        # Find the occupied port
        port_to_free = next(
            (p for p in customer.ports if p.port_status == PortStatus.occupied),
            None,
        )

        # Find the splitter (if the port was found)
        splitter_to_update = None
        if port_to_free:
            splitter_to_update = db.get(Splitter, port_to_free.splitter_id)

        # Find the assigned assets
        ont_asset = next(
            (
                a
                for a in customer.assets
                if a.type == AssetType.ONT and a.status == AssetStatus.assigned
            ),
            None,
        )
        router_asset = next(
            (
                a
                for a in customer.assets
                if a.type == AssetType.Router and a.status == AssetStatus.assigned
            ),
            None,
        )

        # Find the open assignment logs
        now = datetime.now(timezone.utc)
        ont_assignment = next(
            (
                assign
                for assign in customer.asset_assignments
                if ont_asset
                and assign.asset_id == ont_asset.asset_id
                and assign.date_of_return is None
            ),
            None,
        )

        router_assignment = next(
            (
                assign
                for assign in customer.asset_assignments
                if router_asset
                and assign.asset_id == router_asset.asset_id
                and assign.date_of_return is None
            ),
            None,
        )

        # --- 3. Apply all updates ---

        # a) Deactivate Customer
        customer.status = CustomerStatus.Inactive
        db.add(customer)

        # b) Free the Port
        if port_to_free:
            port_to_free.port_status = PortStatus.free
            port_to_free.customer_id = None
            db.add(port_to_free)

        # c) Decrement Splitter count
        if splitter_to_update:
            splitter_to_update.used_ports = max(
                0,
                splitter_to_update.used_ports - 1,
            )  # max(0,...) to prevent going negative
            db.add(splitter_to_update)

        # d) Free the ONT Asset
        if ont_asset:
            ont_asset.status = AssetStatus.available
            ont_asset.assigned_to_customer_id = None
            ont_asset.port_id = None
            db.add(ont_asset)

        # e) Free the Router Asset
        if router_asset:
            router_asset.status = AssetStatus.available
            router_asset.assigned_to_customer_id = None
            db.add(router_asset)

        # f) Close the ONT Assignment Log
        if ont_assignment:
            ont_assignment.date_of_return = now
            ont_assignment.bearing_status = BearingStatus.returned
            db.add(ont_assignment)

        # g) Close the Router Assignment Log
        if router_assignment:
            router_assignment.date_of_return = now
            router_assignment.bearing_status = BearingStatus.returned
            db.add(router_assignment)

        # --- 4. Commit the Transaction ---
        create_audit_log(
            db=db,
            user=current_user,
            action_type=AuditLogActionType.UPDATE,  # Or DELETE, your choice
            description=f"User '{current_user.username}' deactivated customer '{customer.name}' (ID: {customer.customer_id}).",
        )
        db.commit()

        # --- 5. Refresh and return the updated customer ---
        db.refresh(customer)

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:  # noqa: BLE001
        db.rollback()
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred during customer deactivation.",
        )
    else:
        return customer


def get_customer_deactivation_details(
    db: Session,
    customer_id: int,
    current_user: User,
) -> customer_schema.CustomerDeactivationDetailsRead:
    # 1. Get the customer object
    customer = db.get(Customer, customer_id)

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        )

    # 2. Get the provisioning details using our existing function
    # We wrap this in a try/except in case provisioning details are partial
    # or fail for some reason, we can still return the customer.
    try:
        provisioning_details = get_customer_provisioning_details(
            db=db,
            customer_id=customer_id,
            current_user=current_user,
        )
    except Exception as e:  # noqa: BLE001
        # If this fails, we can decide to fail the whole request
        # or return partial data. Failing fast is safer.
        print(f"Error getting provisioning details for customer {customer_id}: {e}")
        # Re-raise a generic error
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load provisioning details for this customer.",
        )

    # 3. Combine them into the new schema
    deactivation_details = customer_schema.CustomerDeactivationDetailsRead(
        customer=customer,
        provisioning=provisioning_details,
    )
    create_audit_log(
        db=db,
        user=current_user,
        action_type=AuditLogActionType.READ,
        description=f"User '{current_user.username}' viewed deactivation details for customer ID {customer_id}.",
    )
    db.commit()

    return deactivation_details
