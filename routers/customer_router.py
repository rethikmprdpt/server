# from typing import Annotated

# from fastapi import APIRouter, Depends, HTTPException, Query, status
# from sqlalchemy.orm import Session

# from db.database import get_db
# from db.models import User, UserRole
# from routers.auth_router import get_current_user
# from schemas import customer as customer_schema
# from schemas import inventory as inventory_schema
# from services import customer as customer_service

# customer_router = APIRouter(prefix="/customers", tags=["Customers"])


# @customer_router.get(
#     "/tree",
#     response_model=inventory_schema.LocationInventory,
# )
# async def get_assets_by_location(
#     db: Annotated[Session, Depends(get_db)],
#     customer_id: int | None,
# ):
#     pass


# @customer_router.post(
#     "/",
#     response_model=customer_schema.CustomerRead,
#     status_code=status.HTTP_201_CREATED,
#     summary="Onboard a new customer",
# )
# def onboard_customer(
#     customer: customer_schema.CustomerCreate,
#     db: Annotated[Session, Depends(get_db)],
# ):
#     try:
#         new_customer = customer_service.create_customer(db=db, customer=customer)
#     except Exception as e:  # noqa: BLE001
#         # A more specific exception might be raised from the service layer
#         raise HTTPException(  # noqa: B904
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"Failed to create customer: {e!s}",
#         )
#     else:
#         return new_customer


# @customer_router.get(
#     "/",
#     response_model=list[customer_schema.CustomerRead],
#     summary="Get customers by status",
# )
# def get_customers_by_status(
#     db: Annotated[Session, Depends(get_db)],
#     status: customer_schema.CustomerStatus = Query(  # noqa: B008, FAST002
#         ...,  # Make the parameter required
#         description="Filter customers by their status",
#     ),
# ):
#     customers = customer_service.get_customers_by_status(db=db, status=status)
#     return customers


# @customer_router.get(
#     "/{customer_id}/provisioning-details",
#     response_model=customer_schema.CustomerProvisioningDetailsRead,
#     summary="Get a customer's provisioned assets and port details",
# )
# def get_provisioning_details(
#     customer_id: int,
#     db: Annotated[Session, Depends(get_db)],
#     # You might want to add your get_current_user dependency here
#     # if only technicians/planners should see this.
# ):
#     details = customer_service.get_customer_provisioning_details(
#         db=db,
#         customer_id=customer_id,
#     )
#     return details


# @customer_router.post(
#     "/{customer_id}/deactivate",
#     response_model=customer_schema.CustomerRead,
#     summary="Deactivate a customer and de-provision all assets",
# )
# def deactivate_customer(
#     customer_id: int,
#     db: Annotated[Session, Depends(get_db)],
#     current_user: Annotated[User, Depends(get_current_user)],
# ):
#     # --- Role-Based Security Check ---
#     if current_user.role not in [UserRole.SupportAgent, UserRole.Admin]:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="You do not have permission to perform this action.",
#         )

#     try:
#         updated_customer = customer_service.deactivate_customer_and_provisioning(
#             db=db,
#             customer_id=customer_id,
#         )
#     except HTTPException as e:
#         # Re-raise known exceptions from the service
#         raise e  # noqa: TRY201
#     except Exception as e:  # noqa: BLE001
#         # Catch any unexpected errors
#         raise HTTPException(  # noqa: B904
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=str(e),
#         )
#     else:
#         return updated_customer


# @customer_router.get(
#     "/{customer_id}/deactivation-details",
#     response_model=customer_schema.CustomerDeactivationDetailsRead,
#     summary="Get all customer and provisioning details for deactivation",
# )
# def get_deactivation_details(
#     customer_id: int,
#     db: Annotated[Session, Depends(get_db)],
#     current_user: Annotated[User, Depends(get_current_user)],
# ):
#     # --- Role-Based Security Check ---
#     if current_user.role not in [UserRole.SupportAgent, UserRole.Admin]:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="You do not have permission to view this information.",
#         )

#     # Call the new service function
#     details = customer_service.get_customer_deactivation_details(
#         db=db,
#         customer_id=customer_id,
#     )
#     return details


# --- routers/customer_router.py (Updated) ---

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import User, UserRole
from routers.auth_router import get_current_user
from schemas import customer as customer_schema
from schemas import inventory as inventory_schema
from services import customer as customer_service

customer_router = APIRouter(prefix="/customers", tags=["Customers"])


@customer_router.get(
    "/tree",
    response_model=inventory_schema.LocationInventory,
)
async def get_assets_by_location(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],  # <-- ADDED
    customer_id: int | None,
):
    # This is a READ, but it's a complex one.
    # We will pass the user to the service in case you want to
    # add a sensitive-read audit log.
    pass


@customer_router.post(
    "/",
    response_model=customer_schema.CustomerRead,
    status_code=status.HTTP_201_CREATED,
    summary="Onboard a new customer",
)
def onboard_customer(
    customer: customer_schema.CustomerCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],  # <-- ADDED
):
    try:
        # --- UPDATED: Pass current_user to the service ---
        new_customer = customer_service.create_customer(
            db=db,
            customer=customer,
            current_user=current_user,
        )
    except Exception as e:  # noqa: BLE001
        # A more specific exception might be raised from the service layer
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create customer: {e!s}",
        )
    else:
        return new_customer


@customer_router.get(
    "/",
    response_model=list[customer_schema.CustomerRead],
    summary="Get customers by status",
)
def get_customers_by_status(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],  # <-- ADDED
    status: customer_schema.CustomerStatus = Query(  # noqa: B008, FAST002
        ...,  # Make the parameter required
        description="Filter customers by their status",
    ),
):
    # Pass user in case you want to secure this or log it
    customers = customer_service.get_customers_by_status(
        db=db,
        status=status,
        current_user=current_user,
    )
    return customers


@customer_router.get(
    "/{customer_id}/provisioning-details",
    response_model=customer_schema.CustomerProvisioningDetailsRead,
    summary="Get a customer's provisioned assets and port details",
)
def get_provisioning_details(
    customer_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],  # <-- ADDED
):
    # This is a sensitive READ, so we pass the user
    details = customer_service.get_customer_provisioning_details(
        db=db,
        customer_id=customer_id,
        current_user=current_user,
    )
    return details


@customer_router.post(
    "/{customer_id}/deactivate",
    response_model=customer_schema.CustomerRead,
    summary="Deactivate a customer and de-provision all assets",
)
def deactivate_customer(
    customer_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    # --- Role-Based Security Check ---
    if current_user.role not in [UserRole.SupportAgent, UserRole.Admin]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action.",
        )

    try:
        # --- UPDATED: Pass current_user to the service ---
        updated_customer = customer_service.deactivate_customer_and_provisioning(
            db=db,
            customer_id=customer_id,
            current_user=current_user,
        )
    except HTTPException as e:
        # Re-raise known exceptions from the service
        raise e  # noqa: TRY201
    except Exception as e:  # noqa: BLE001
        # Catch any unexpected errors
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    else:
        return updated_customer


@customer_router.get(
    "/{customer_id}/deactivation-details",
    response_model=customer_schema.CustomerDeactivationDetailsRead,
    summary="Get all customer and provisioning details for deactivation",
)
def get_deactivation_details(
    customer_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    # --- Role-Based Security Check ---
    if current_user.role not in [UserRole.SupportAgent, UserRole.Admin]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this information.",
        )

    # Call the service function
    # --- UPDATED: Pass current_user to the service ---
    details = customer_service.get_customer_deactivation_details(
        db=db,
        customer_id=customer_id,
        current_user=current_user,
    )
    return details
