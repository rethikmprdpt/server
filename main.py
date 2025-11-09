# from contextlib import asynccontextmanager

# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware

# from db import models  # noqa: F401
# from db.base import Base  # noqa: F401
# from db.database import engine
# from routers.asset_router import asset_router
# from routers.inventory_router import inventory_router

# origins = [
#     "http://localhost",
#     "http://localhost:5173",
# ]


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     print("INFO:     Application startup...")
#     print("INFO:     Database engine is ready (connections are lazy).")

#     yield

#     print("INFO:     Application shutdown...")
#     engine.dispose()
#     print("INFO:     Database connections closed.")


# app = FastAPI(lifespan=lifespan)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
# app.include_router(asset_router)
# app.include_router(inventory_router)


# @app.get("/")
# async def root():
#     return {"message": "Server is running"}


import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

import db.models  # noqa: F401
from db.base import Base
from db.database import engine
from routers.asset_router import asset_router
from routers.audit_router import audit_router
from routers.auth_router import auth_router
from routers.customer_router import customer_router
from routers.deployment_router import deployment_router
from routers.fdh_router import fdh_router
from routers.inventory_router import inventory_router
from routers.splitter_router import splitter_router
from routers.user_router import user_router

log = logging.getLogger(__name__)

origins = [
    "http://localhost",
    "http://localhost:5173",
]


def init_db(engine: Engine):
    try:
        log.info("Initializing database...")
        log.info("Checking and creating tables...")
        Base.metadata.create_all(bind=engine)
        log.info("Tables created successfully (if they didn't exist).")
    except SQLAlchemyError as e:
        log.error(f"Error creating tables: {e}")
        raise
    except Exception as e:
        log.error(f"An unexpected error occurred during table creation: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Application startup...")

    try:
        init_db(engine)
        log.info("Database initialization complete.")
    except Exception as e:
        log.critical(f"Database initialization failed: {e}.")

    yield

    log.info("Application shutdown...")
    engine.dispose()
    log.info("Database connections closed.")


app = FastAPI(
    title="Inventory Management System API",
    description="API for managing assets, FDHs, splitters, and customers.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(asset_router)
app.include_router(inventory_router)
app.include_router(customer_router)
app.include_router(deployment_router)
app.include_router(user_router)
app.include_router(fdh_router)
app.include_router(audit_router)
app.include_router(splitter_router)


@app.get("/", tags=["Root"])
async def root():
    return {"message": "Welcome to the Inventory Management System API"}
