# seed.py
import random

from faker import Faker
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.base import Base

# --- IMPORT YOUR DB SETUP AND MODELS ---
# (Adjust these imports based on your file structure)
from db.database import SessionLocal, engine
from db.models import (
    FDH,
    Asset,
    AssetAssignment,
    AssetStatus,
    AssetType,
    BearingStatus,
    Customer,
    CustomerStatus,
    Port,
    PortStatus,
    Splitter,
    SplitterStatus,
    Warehouse,
)

# Initialize Faker
fake = Faker()


def clear_data(db: Session):
    """
    Deletes all data from the tables in the correct order
    to avoid foreign key constraint errors.
    """
    print("Clearing all existing data...")

    # Delete in reverse order of creation/dependency
    db.query(AssetAssignment).delete()
    db.query(Asset).delete()
    db.query(Port).delete()
    db.query(Customer).delete()
    db.query(Splitter).delete()
    db.query(FDH).delete()
    db.query(Warehouse).delete()

    db.commit()
    print("Data cleared.")


def seed_data(db: Session):
    """
    Populates the database with fake data.
    """
    print("Seeding new data...")

    try:
        # --- 1. Create items with no dependencies ---

        warehouses = [
            Warehouse(address=fake.street_address(), pincode=fake.zipcode()[:6])
            for _ in range(5)
        ]
        db.add_all(warehouses)

        fdhs = [
            FDH(
                model=random.choice(["FDH-100", "FDH-200", "FDH-300"]),
                pincode=fake.zipcode()[:6],
                latitude=fake.latitude(),
                longitude=fake.longitude(),
            )
            for _ in range(10)
        ]
        db.add_all(fdhs)

        customers = [
            Customer(
                name=fake.name(),
                address=fake.address(),
                pincode=fake.zipcode()[:6],
                plan=random.choice(["Basic-100", "Premium-500", "Pro-1000"]),
                status=fake.enum(CustomerStatus),
            )
            for _ in range(50)
        ]
        db.add_all(customers)

        # Commit to get IDs for the next batch
        db.commit()
        print("Created Warehouses, FDHs, and Customers.")

        # --- 2. Create items that depend on Step 1 ---

        splitters = [
            Splitter(
                model=random.choice(["SPL-1x8", "SPL-1x16", "SPL-1x32"]),
                status=fake.enum(SplitterStatus),
                max_ports=16,
                used_ports=0,  # We'll update this later
                fdh_id=random.choice(fdhs).fdh_id,
            )
            for _ in range(30)
        ]
        db.add_all(splitters)
        db.commit()
        print("Created Splitters.")

        # --- 3. Create items that depend on Step 1 & 2 ---

        ports = []
        for splitter in splitters:
            # Create a few ports for each splitter
            num_ports_to_create = random.randint(4, splitter.max_ports)
            splitter.used_ports = num_ports_to_create  # Update used_ports

            for _ in range(num_ports_to_create):
                # 80% chance port is occupied, 20% free
                is_occupied = random.random() < 0.8
                port_status = PortStatus.occupied if is_occupied else PortStatus.free

                ports.append(
                    Port(
                        port_status=port_status,
                        # If occupied, assign a customer. If free, leave as None.
                        customer_id=random.choice(customers).customer_id
                        if is_occupied
                        else None,
                        splitter_id=splitter.splitter_id,
                    )
                )
        db.add_all(ports)
        db.commit()
        print("Created Ports.")

        # --- 4. Create Assets ---

        assets = []
        for _ in range(100):
            # 50% assigned to customer, 50% in warehouse
            is_assigned = random.random() < 0.5

            assets.append(
                Asset(
                    type=fake.enum(AssetType),
                    model=random.choice(["Model-X", "Model-Y", "Model-Z"]),
                    serial_number=fake.unique.ssn(),  # Using ssn for a unique string
                    status=AssetStatus.assigned
                    if is_assigned
                    else AssetStatus.available,
                    pincode=fake.zipcode()[:6],
                    assigned_to_customer_id=random.choice(customers).customer_id
                    if is_assigned
                    else None,
                    stored_at_warehouse_id=None
                    if is_assigned
                    else random.choice(warehouses).warehouse_id,
                    port_id=None,  # We can assign this later or leave as null
                )
            )
        db.add_all(assets)
        db.commit()
        print("Created Assets.")

        # --- 5. Create Asset Assignments (History) ---

        # Find just the assigned assets
        assigned_assets = [a for a in assets if a.status == AssetStatus.assigned]

        assignments = [
            AssetAssignment(
                asset_id=asset.asset_id,
                bearing_status=BearingStatus.bearing,
                date_of_issue=fake.date_time_this_year(),
                customer_id=asset.assigned_to_customer_id,
            )
            for asset in assigned_assets
        ]
        db.add_all(assignments)
        db.commit()
        print("Created Asset Assignments.")

        print("\n--- Seeding complete! ---")

    except IntegrityError as e:
        print(
            f"Error: An integrity constraint failed (e.g., duplicate key). Rolling back. {e}"
        )
        db.rollback()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        db.rollback()


if __name__ == "__main__":
    # This block runs when you execute the script directly

    # Optional: You can create a fresh, empty DB every time
    # Base.metadata.drop_all(bind=engine)
    # Base.metadata.create_all(bind=engine)
    # print("Tables dropped and recreated.")

    db = SessionLocal()
    try:
        clear_data(db)  # Start from a clean slate
        seed_data(db)  # Populate with new data
    finally:
        db.close()
        print("Database session closed.")
