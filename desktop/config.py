from pathlib import Path
import os

APP_NAME = "Neighbourhood Water Management"
APP_DIR = Path(os.getenv("PROGRAMDATA", Path.home())) / "NeighbourhoodWaterManagement"
APP_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = APP_DIR / "water_management.db"
DATABASE_URL = os.getenv("NWM_DATABASE_URL", f"sqlite:///{DB_PATH.as_posix()}")
CURRENCY = "KES"
DEFAULT_DUE_DAY = 10
NEIGHBOURHOOD_NAME = "Neighbourhood Water Management"
