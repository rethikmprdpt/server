class AssetError(Exception):
    def __init__(self, message, asset_id=None):
        super().__init__(message)

        self.message = message
        self.asset_id = asset_id

    def __str__(self):
        if self.asset_id:
            return f"AssetError [Asset ID: {self.asset_id}]: {self.message}"
        return f"AssetError: {self.message}"
