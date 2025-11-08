import sys

from sqlalchemy.orm import Session

# --- Adjust these imports to match your project structure ---
try:
    # Assumes 'database.py' in root, with SessionLocal and engine
    # Assumes 'models/' folder, with 'base.py' and 'user.py'
    from db.base import Base
    from db.database import SessionLocal, engine

    # This line now imports the UserRole enum you provided
    from db.models import User, UserRole

    # Assumes 'utils/auth.py'
    from utils.auth import get_password_hash
except ImportError as e:
    print(f"Error: Could not import modules. Check paths. {e}")
    print(
        "Please make sure 'database.py', 'models/base.py', 'models/user.py', and 'utils/auth.py' are accessible."
    )
    sys.exit(1)

# ### --- UPDATED SECTION --- ###
# This list now matches your UserRole enum
# (You can change these passwords)
users_to_create = [
    {"username": "admin", "password": "admin123", "role": UserRole.Admin},
    {"username": "planner", "password": "planner123", "role": UserRole.Planner},
    {"username": "tech", "password": "tech123", "role": UserRole.Technician},
    {"username": "support", "password": "support123", "role": UserRole.SupportAgent},
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


def seed_users():
    """Seeds the database with dummy users."""
    print("Seeding users...")
    db: Session = SessionLocal()
    try:
        for user_data in users_to_create:
            # Check if user already exists
            existing_user = (
                db.query(User).filter(User.username == user_data["username"]).first()
            )

            if not existing_user:
                # Hash the password
                hashed_password = get_password_hash(user_data["password"])

                # Create new user object
                new_user = User(
                    username=user_data["username"],
                    password_hash=hashed_password,
                    role=user_data["role"],
                )
                db.add(new_user)
                print(f"  [+] User '{user_data['username']}' created.")
            else:
                print(f"  [*] User '{user_data['username']}' already exists. Skipping.")

        db.commit()
        print("Users seeded successfully.")

    except Exception as e:
        print(f"An error occurred during seeding: {e}")
        db.rollback()

    finally:
        db.close()


if __name__ == "__main__":
    create_tables()
    seed_users()
