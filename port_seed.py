import sys

from sqlalchemy import func, select  # <-- Added func import
from sqlalchemy.orm import Session

# --- Adjust these imports to match your project structure ---
try:
    from db.base import Base
    from db.database import SessionLocal, engine

    # --- UPDATED IMPORTS ---
    # Import all models and enums needed
    from db.models import (
        FDH,
        AssetStatus,
        Customer,
        CustomerStatus,
        Port,
        PortStatus,
        Splitter,
        User,
        UserRole,
    )
    # --- REMOVED get_password_hash ---
except ImportError as e:
    print(f"Error: Could not import modules. Check paths. {e}")
    print("Please make sure all models are imported correctly from db/models.py")
    sys.exit(1)

# --- Data for Seeding ---

# --- REMOVED users_to_create list ---

# --- REMOVED customers_to_create, fdhs_to_create, splitters_to_create ---
# We will use the existing data in your database.

ports_to_create = [
    {"splitter_id": 1, "count": 8},
    {"splitter_id": 2, "count": 16},
    {"splitter_id": 3, "count": 8},
    {"splitter_id": 4, "count": 32},
]


# --- Main Seeding Functions ---


def create_tables():
    """Creates all tables in the database."""
    print("Creating tables (if they don't exist)...")
    try:
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully (or already exist).")
    except Exception as e:
        print(f"Error creating tables: {e}")
        sys.exit(1)


# --- REMOVED generic seed_data function ---

# --- REMOVED seed_users function ---


def seed_ports(db: Session):
    """Seeds the database with ports for each splitter."""
    print("Seeding Ports...")
    try:
        count = 0
        for splitter_data in ports_to_create:
            splitter_id = splitter_data["splitter_id"]

            # --- Check if splitter exists before adding ports ---
            splitter = db.get(Splitter, splitter_id)
            if not splitter:
                print(
                    f"  [!] Splitter {splitter_id} not found. Skipping port creation."
                )
                continue  # Skip to the next splitter

            # Check if ports already exist for this splitter
            existing_ports_count = db.scalar(
                select(func.count(Port.port_id)).where(Port.splitter_id == splitter_id)
            )

            if existing_ports_count == 0:
                print(
                    f"  [*] Creating {splitter_data['count']} ports for splitter {splitter_id}..."
                )
                for _ in range(splitter_data["count"]):
                    new_port = Port(
                        splitter_id=splitter_id, port_status=PortStatus.free
                    )
                    db.add(new_port)
                    count += 1
            else:
                print(
                    f"  [*] Splitter {splitter_id} already has {existing_ports_count} ports. Skipping."
                )

        db.commit()
        if count > 0:
            print(f"  [+] {count} new Port(s) created.")
        print("Ports seeded successfully.")

    except Exception as e:
        print(f"An error occurred during port seeding: {e}")
        db.rollback()


def create_assignments(db: Session):
    """Assigns customers to ports and updates splitter counts as requested."""
    print("Creating assignments...")
    try:
        # --- Assignment 1 & 2: Customer 1 and 3 to Splitter 1 ---
        spl1 = db.get(Splitter, 1)
        cust1 = db.get(Customer, 1)
        cust3 = db.get(Customer, 3)

        if spl1 and cust1 and cust3:
            if spl1.used_ports == 0:  # Only run if not already assigned
                free_ports_s1 = db.scalars(
                    select(Port)
                    .where(Port.splitter_id == 1, Port.port_status == PortStatus.free)
                    .limit(2)
                ).all()

                if len(free_ports_s1) == 2:
                    free_ports_s1[0].customer_id = 1
                    free_ports_s1[0].port_status = PortStatus.occupied
                    free_ports_s1[1].customer_id = 3
                    free_ports_s1[1].port_status = PortStatus.occupied
                    spl1.used_ports = 2

                    db.add_all([free_ports_s1[0], free_ports_s1[1], spl1])
                    db.commit()
                    print("  [+] Assigned Customer 1 and 3 to ports on Splitter 1.")
                else:
                    print(
                        "  [*] Not enough free ports on Splitter 1. Skipping assignment."
                    )
            else:
                print("  [*] Splitter 1 assignments already exist. Skipping.")
        else:
            print("  [*] Splitter 1 or Customers 1/3 not found. Skipping assignment.")

        # --- Assignment 3: Customer 2 to Splitter 4 ---
        spl4 = db.get(Splitter, 4)
        cust2 = db.get(Customer, 2)

        if spl4 and cust2:
            if spl4.used_ports == 0:  # Only run if not already assigned
                free_port_s4 = db.scalar(
                    select(Port)
                    .where(Port.splitter_id == 4, Port.port_status == PortStatus.free)
                    .limit(1)
                )

                if free_port_s4:
                    free_port_s4.customer_id = 2
                    free_port_s4.port_status = PortStatus.occupied
                    spl4.used_ports = 1

                    db.add_all([free_port_s4, spl4])
                    db.commit()
                    print("  [+] Assigned Customer 2 to a port on Splitter 4.")
                else:
                    print("  [*] No free ports on Splitter 4. Skipping assignment.")
            else:
                print("  [*] Splitter 4 assignment already exists. Skipping.")
        else:
            print("  [*] Splitter 4 or Customer 2 not found. Skipping assignment.")

        print("Assignments completed.")

    except Exception as e:
        print(f"An error occurred during assignments: {e}")
        db.rollback()


if __name__ == "__main__":
    db = SessionLocal()
    try:
        create_tables()
        # --- REMOVED seed_users(db) call ---
        # --- REMOVED FDH, SPLITTER, CUSTOMER SEEDING ---
        seed_ports(db)  # Creates ports for existing splitters
        create_assignments(db)  # Assigns existing customers to new ports
    finally:
        db.close()
        print("Database session closed.")
