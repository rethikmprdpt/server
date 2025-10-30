import os
import sys
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

from alembic import context
from db import models
from db.base import Base

# Load the .env file
# This makes os.environ['DATABASE_URL'] available
load_dotenv()
# --- END OF BLOCK ---


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# --- ADD THIS BLOCK ---
# This adds your project's root directory to the Python path
# so that alembic can find your 'base' and 'models' modules.
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))  # noqa: PTH118, PTH120

# Import your Base from base.py
# Import your models.py file
# This is crucial so that Base.metadata knows about your tables.


# --- END OF BLOCK ---


# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata

# --- EDIT THIS LINE ---
# Point target_metadata to your Base object's metadata
target_metadata = Base.metadata
# --- END OF EDIT ---


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    # This will now correctly read the URL from your .env file
    # (via the alembic.ini's %(DATABASE_URL)s setting)
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # This function will also correctly read the URL
    # from your .env file via alembic.ini
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
