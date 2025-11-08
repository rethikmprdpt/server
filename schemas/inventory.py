from pydantic import BaseModel

from .asset import AssetRead, FdhRead, SplitterRead


class LocationInventory(BaseModel):
    pincode: str
    assets: list[AssetRead]
    fdhs: list[FdhRead]
    splitters: list[SplitterRead]
