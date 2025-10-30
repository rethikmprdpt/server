from contextlib import asynccontextmanager

from fastapi import FastAPI

from db import models  # noqa: F401
from db.base import Base  # noqa: F401
from db.database import engine
from routers.asset_router import asset_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("INFO:     Application startup...")
    print("INFO:     Database engine is ready (connections are lazy).")

    yield

    print("INFO:     Application shutdown...")
    engine.dispose()
    print("INFO:     Database connections closed.")


app = FastAPI(lifespan=lifespan)
app.include_router(asset_router)


@app.get("/")
async def root():
    return {"message": "Server is running"}
