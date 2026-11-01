from sqlalchemy import String, Integer, Date, DateTime, ForeignKey, Numeric, Boolean, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from decimal import Decimal
from database import Base

class Household(Base):
    __tablename__ = "households"
    id: Mapped[int] = mapped_column(primary_key=True)
    house_number: Mapped[str] = mapped_column(String(50), unique=True)
    owner_name: Mapped[str] = mapped_column(String(150), default="")
    tenant_name: Mapped[str] = mapped_column(String(150), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    location: Mapped[str] = mapped_column(String(150), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    meters: Mapped[list["Meter"]] = relationship(back_populates="household")

class Meter(Base):
    __tablename__ = "meters"
    id: Mapped[int] = mapped_column(primary_key=True)
    serial_number: Mapped[str] = mapped_column(String(80), unique=True)
    meter_type: Mapped[str] = mapped_column(String(20))
    household_id: Mapped[int | None] = mapped_column(ForeignKey("households.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    installed_on: Mapped[Date | None] = mapped_column(Date, nullable=True)
    household: Mapped[Household | None] = relationship(back_populates="meters")

class Reading(Base):
    __tablename__ = "readings"
    __table_args__ = (UniqueConstraint("meter_id", "period", name="uq_meter_period"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    meter_id: Mapped[int] = mapped_column(ForeignKey("meters.id"))
    period: Mapped[str] = mapped_column(String(30))
    previous_value: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    current_value: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    consumption: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    recorded_by: Mapped[str] = mapped_column(String(100), default="Administrator")
    approved: Mapped[bool] = mapped_column(Boolean, default=True)

class WaterPrice(Base):
    __tablename__ = "water_prices"
    id: Mapped[int] = mapped_column(primary_key=True)
    price_per_m3: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    effective_from: Mapped[Date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

class Bill(Base):
    __tablename__ = "bills"
    __table_args__ = (UniqueConstraint("household_id", "period", name="uq_household_period"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    bill_number: Mapped[str] = mapped_column(String(50), unique=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id"))
    period: Mapped[str] = mapped_column(String(30))
    consumption: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    water_charge: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    arrears: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    total_due: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    due_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Unpaid")

class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey("bills.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    method: Mapped[str] = mapped_column(String(30))
    reference: Mapped[str] = mapped_column(String(100), default="")
    paid_on: Mapped[Date] = mapped_column(Date)
    recorded_by: Mapped[str] = mapped_column(String(100), default="Administrator")
    reversed: Mapped[bool] = mapped_column(Boolean, default=False)

class Reconciliation(Base):
    __tablename__ = "reconciliations"
    id: Mapped[int] = mapped_column(primary_key=True)
    period: Mapped[str] = mapped_column(String(30), unique=True)
    main_consumption: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    submeter_consumption: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    difference: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    method: Mapped[str] = mapped_column(String(40))
    notes: Mapped[str] = mapped_column(Text, default="")
    approved_by: Mapped[str] = mapped_column(String(100), default="Administrator")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class BillingPeriod(Base):
    __tablename__ = "billing_periods"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30), unique=True)
    start_date: Mapped[Date] = mapped_column(Date)
    end_date: Mapped[Date] = mapped_column(Date)
    due_date: Mapped[Date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="Open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), default="Administrator")
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(80), default="")
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

class MeterReplacement(Base):
    __tablename__ = "meter_replacements"
    id: Mapped[int] = mapped_column(primary_key=True)
    old_meter_id: Mapped[int] = mapped_column(ForeignKey("meters.id"))
    new_meter_id: Mapped[int] = mapped_column(ForeignKey("meters.id"))
    old_final_reading: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    new_initial_reading: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    replacement_date: Mapped[Date] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(Text, default="")
    authorized_by: Mapped[str] = mapped_column(String(100), default="Administrator")


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(30), default="Operator")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

class PaymentAllocation(Base):
    __tablename__ = "payment_allocations"
    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), index=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey("bills.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class SyncRequest(Base):
    __tablename__ = "sync_requests"
    request_key: Mapped[str] = mapped_column(String(120), primary_key=True)
    device_id: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(30))
    payload_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="processing")
    response_json: Mapped[str] = mapped_column(Text, default="{}")
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
