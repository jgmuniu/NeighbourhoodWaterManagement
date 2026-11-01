from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import DATABASE_URL

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def initialize_database():
    from models import Household, Meter, Reading, WaterPrice, Bill, Payment, Reconciliation, BillingPeriod, AuditLog, MeterReplacement, User, PaymentAllocation, SyncRequest
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    if "bills" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("bills")}
        with engine.begin() as connection:
            if "due_date" not in columns:
                connection.execute(text("ALTER TABLE bills ADD COLUMN due_date DATE"))
            if "status" not in columns:
                connection.execute(text("ALTER TABLE bills ADD COLUMN status VARCHAR(20) DEFAULT 'Unpaid'"))
