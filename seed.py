import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# passlib removed
# --- Project Imports ---
# Import the session and all models from your project files
from db.database import SessionLocal
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
    # User, UserRole, and AuditLog removed
)

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# --- Password Hashing Setup Removed ---


def truncate_and_fix_tables(session):
    """
    Truncates all data tables and fixes the splitters.status column schema
    to match the AssetStatus enum.
    """
    log.info("--- Preparing Database: Disabling Foreign Keys ---")
    try:
        # Use 'inventorymanager' schema as seen in your logs
        schema_name = "inventorymanager"

        session.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))

        # --- FIX SCHEMA MISMATCH ---
        log.info("Fixing splitters.status column schema...")
        alter_stmt = text(
            f"ALTER TABLE {schema_name}.splitters MODIFY status VARCHAR(10) NOT NULL"
        )
        session.execute(alter_stmt)
        log.info("Column 'splitters.status' fixed.")

        # --- TRUNCATE TABLES ---
        tables = [
            "asset_assignments",
            "assets",
            "ports",
            "splitters",
            "customers",
            "fdhs",
            # "audit_logs" and "users" removed
        ]
        for table in tables:
            log.info(f"Truncating {schema_name}.{table}...")
            session.execute(text(f"TRUNCATE TABLE {schema_name}.{table};"))

        log.info("All tables truncated.")

        # --- RE-ENABLE KEYS ---
        session.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
        log.info("--- Database Prep Finished: Foreign Keys Re-enabled ---")

        session.commit()
    except SQLAlchemyError as e:
        log.error(f"Error during table preparation: {e}")
        session.rollback()
        raise


def seed_data(session):
    """Inserts new, interconnected seed data."""
    log.info("--- Seeding New Data ---")

    # --- Pincodes (5 Chennai Pincodes) ---
    pincodes = ["600001", "600017", "600041", "600028", "600086"]

    try:
        # --- 1. Users block removed ---

        # --- 2. FDHs (Fiber Distribution Hubs) ---
        fdh1_p1 = FDH(
            model="Nokia FX-8",
            pincode=pincodes[0],
            latitude=Decimal("13.0880"),
            longitude=Decimal("80.2821"),
        )
        fdh2_p1 = FDH(
            model="Huawei MA5600T",
            pincode=pincodes[0],
            latitude=Decimal("13.0885"),
            longitude=Decimal("80.2825"),
        )
        fdh1_p2 = FDH(
            model="Nokia FX-8",
            pincode=pincodes[1],
            latitude=Decimal("13.0400"),
            longitude=Decimal("80.2300"),
        )
        fdh1_p3 = FDH(
            model="ZTE C300",
            pincode=pincodes[2],
            latitude=Decimal("13.0010"),
            longitude=Decimal("80.2550"),
        )
        session.add_all([fdh1_p1, fdh2_p1, fdh1_p2, fdh1_p3])
        session.flush()
        log.info("FDHs created.")

        # --- 3. Splitters ---
        sp1_f1 = Splitter(
            model="1:8 Passive", status=AssetStatus.available, max_ports=8, fdh=fdh1_p1
        )
        sp2_f1 = Splitter(
            model="1:16 Passive",
            status=AssetStatus.available,
            max_ports=16,
            fdh=fdh1_p1,
        )
        sp1_f2 = Splitter(
            model="1:8 Passive", status=AssetStatus.available, max_ports=8, fdh=fdh2_p1
        )
        sp1_f3 = Splitter(
            model="1:32 Passive",
            status=AssetStatus.available,
            max_ports=32,
            fdh=fdh1_p2,
        )
        session.add_all([sp1_f1, sp2_f1, sp1_f2, sp1_f3])
        session.flush()
        log.info("Splitters created.")

        # --- 4. Ports ---
        ports_sp1 = [
            Port(port_status=PortStatus.free, splitter=sp1_f1)
            for _ in range(sp1_f1.max_ports)
        ]
        ports_sp2 = [
            Port(port_status=PortStatus.free, splitter=sp2_f1)
            for _ in range(sp2_f1.max_ports)
        ]
        ports_sp3 = [
            Port(port_status=PortStatus.free, splitter=sp1_f3)
            for _ in range(sp1_f3.max_ports)
        ]
        session.add_all(ports_sp1 + ports_sp2 + ports_sp3)
        session.flush()
        log.info("Ports created.")

        # --- 5. Customers ---
        cust1 = Customer(
            name="Arun Kumar",
            address="12, NSC Bose Road, Parrys",
            pincode=pincodes[0],
            plan="Fiber Gold 100Mbps",
            status=CustomerStatus.Active,
        )
        cust2 = Customer(
            name="Priya Selvam",
            address="45, Usman Road, T. Nagar",
            pincode=pincodes[1],
            plan="Fiber Platinum 300Mbps",
            status=CustomerStatus.Active,
        )
        cust3 = Customer(
            name="Suresh Gupta",
            address="8, Mint Street, Sowcarpet",
            pincode=pincodes[0],
            plan="Fiber Silver 50Mbps",
            status=CustomerStatus.Active,
        )
        cust4 = Customer(
            name="Anita Desai",
            address="22, Thyagaraya Road, T. Nagar",
            pincode=pincodes[1],
            plan="Fiber Gold 100Mbps",
            status=CustomerStatus.Pending,
        )
        cust5 = Customer(
            name="Rajesh Kannan",
            address="10, St Marys Road, Alwarpet",
            pincode=pincodes[2],
            plan="Fiber Gold 100Mbps",
            status=CustomerStatus.Inactive,
        )
        session.add_all([cust1, cust2, cust3, cust4, cust5])
        session.flush()
        log.info("Customers created.")

        # --- 6. Assets (ONTs and Routers) ---
        ont1_w1 = Asset(
            type=AssetType.ONT,
            model="Nokia G-140W-C",
            serial_number="NK12345678",
            status=AssetStatus.available,
            pincode=pincodes[0],
        )
        rtr1_w1 = Asset(
            type=AssetType.Router,
            model="TP-Link Archer C6",
            serial_number="TP12345678",
            status=AssetStatus.available,
            pincode=pincodes[0],
        )
        ont2_w1 = Asset(
            type=AssetType.ONT,
            model="Huawei HG8245H",
            serial_number="HW12345678",
            status=AssetStatus.available,
            pincode=pincodes[0],
        )
        ont3_w2 = Asset(
            type=AssetType.ONT,
            model="Nokia G-140W-C",
            serial_number="NK98765432",
            status=AssetStatus.available,
            pincode=pincodes[1],
        )
        rtr2_w2 = Asset(
            type=AssetType.Router,
            model="D-Link DIR-825",
            serial_number="DL98765432",
            status=AssetStatus.available,
            pincode=pincodes[1],
        )
        rtr3_w2 = Asset(
            type=AssetType.Router,
            model="TP-Link Archer C6",
            serial_number="TP98765432",
            status=AssetStatus.available,
            pincode=pincodes[1],
        )
        ont4_p3 = Asset(
            type=AssetType.ONT,
            model="ZTE F609",
            serial_number="ZT55555555",
            status=AssetStatus.available,
            pincode=pincodes[2],
        )
        rtr4_p4 = Asset(
            type=AssetType.Router,
            model="Netgear R6120",
            serial_number="NG44444444",
            status=AssetStatus.faulty,
            pincode=pincodes[3],
        )
        session.add_all(
            [ont1_w1, rtr1_w1, ont2_w1, ont3_w2, rtr2_w2, rtr3_w2, ont4_p3, rtr4_p4]
        )
        session.flush()
        log.info("Assets created.")

        # --- 7. Chain Customer 1 (Arun Kumar @ 600001) ---
        log.info("Chaining Customer 1 (Arun Kumar)...")
        port_for_cust1 = ports_sp1[0]
        port_for_cust1.port_status = PortStatus.occupied
        port_for_cust1.customer = cust1

        ont_for_cust1 = ont1_w1
        ont_for_cust1.status = AssetStatus.assigned
        ont_for_cust1.pincode = cust1.pincode
        ont_for_cust1.customer = cust1
        ont_for_cust1.port = port_for_cust1

        rtr_for_cust1 = rtr1_w1
        rtr_for_cust1.status = AssetStatus.assigned
        rtr_for_cust1.pincode = cust1.pincode
        rtr_for_cust1.customer = cust1

        assign1_ont = AssetAssignment(
            asset=ont_for_cust1,
            bearing_status=BearingStatus.bearing,
            date_of_issue=datetime.now(timezone.utc),
            customer=cust1,
        )
        assign1_rtr = AssetAssignment(
            asset=rtr_for_cust1,
            bearing_status=BearingStatus.bearing,
            date_of_issue=datetime.now(timezone.utc),
            customer=cust1,
        )
        session.add_all(
            [port_for_cust1, ont_for_cust1, rtr_for_cust1, assign1_ont, assign1_rtr]
        )

        # --- 8. Chain Customer 2 (Priya Selvam @ 600017) ---
        log.info("Chaining Customer 2 (Priya Selvam)...")
        port_for_cust2 = ports_sp3[0]
        port_for_cust2.port_status = PortStatus.occupied
        port_for_cust2.customer = cust2

        ont_for_cust2 = ont3_w2
        ont_for_cust2.status = AssetStatus.assigned
        ont_for_cust2.pincode = cust2.pincode
        ont_for_cust2.customer = cust2
        ont_for_cust2.port = port_for_cust2

        rtr_for_cust2 = rtr2_w2
        rtr_for_cust2.status = AssetStatus.assigned
        rtr_for_cust2.pincode = cust2.pincode
        rtr_for_cust2.customer = cust2

        assign2_ont = AssetAssignment(
            asset=ont_for_cust2,
            bearing_status=BearingStatus.bearing,
            date_of_issue=datetime.now(timezone.utc),
            customer=cust2,
        )
        assign2_rtr = AssetAssignment(
            asset=rtr_for_cust2,
            bearing_status=BearingStatus.bearing,
            date_of_issue=datetime.now(timezone.utc),
            customer=cust2,
        )
        session.add_all(
            [port_for_cust2, ont_for_cust2, rtr_for_cust2, assign2_ont, assign2_rtr]
        )

        # --- 9. Update Splitter Port Counts ---
        sp1_f1.used_ports = 1
        sp1_f3.used_ports = 1
        log.info("Customer chains created and ports updated.")

        # --- 10. Audit Log Entry Removed ---

        # --- Commit ---
        session.commit()
        log.info("--- Seed Data Committed Successfully! ---")

    except SQLAlchemyError as e:
        log.error(f"Error seeding data: {e}")
        session.rollback()
    except Exception as e:
        log.error(f"An unexpected error occurred: {e}")
        session.rollback()


def main():
    log.info("--- Starting Seed Script ---")

    db = SessionLocal()
    try:
        # Step 1: Fix schema and truncate all tables
        truncate_and_fix_tables(db)

        # Step 2: Seed fresh data
        seed_data(db)

    except Exception as e:
        log.error(f"Seeding script failed: {e}")
    finally:
        db.close()

    log.info("--- Seed Script Finished ---")


if __name__ == "__main__":
    main()
