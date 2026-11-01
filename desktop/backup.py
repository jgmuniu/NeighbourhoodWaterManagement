import argparse
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from sqlalchemy import text
from config import DB_PATH, DATABASE_URL
from database import engine


def create_backup(destination_dir):
    folder = Path(destination_dir).expanduser().resolve()
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if engine.dialect.name == "sqlite":
        source = Path(engine.url.database).expanduser().resolve() if engine.url.database else None
        if source is None or not source.is_file():
            raise RuntimeError("The configured SQLite database is not a file-backed database.")
        target = folder / f"nwm_backup_{stamp}.db"
        if source == target.resolve():
            raise RuntimeError("Choose a backup destination separate from the live database.")
        with engine.connect() as connection:
            connection.execute(text("PRAGMA wal_checkpoint(FULL)"))
        shutil.copy2(source, target)
        return target
    if engine.dialect.name == "postgresql":
        target = folder / f"nwm_backup_{stamp}.dump"
        result = subprocess.run(["pg_dump", "--format=custom", "--file", str(target), DATABASE_URL],
                                capture_output=True, text=True)
        if result.returncode:
            target.unlink(missing_ok=True)
            raise RuntimeError(result.stderr.strip() or "pg_dump failed.")
        return target
    raise RuntimeError(f"Unsupported database engine: {engine.dialect.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a timestamped Neighbourhood Water Management backup")
    parser.add_argument("destination", help="Folder for the backup file")
    args = parser.parse_args()
    print(create_backup(args.destination))
