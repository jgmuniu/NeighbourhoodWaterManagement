from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from database import SessionLocal
from models import Household, Meter, Reading, WaterPrice, Bill, Payment, Reconciliation, BillingPeriod, AuditLog, MeterReplacement, User, PaymentAllocation

CENT = Decimal("0.01")

def money(value):
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)

def add_household(house_number, owner, tenant, phone, location):
    with SessionLocal() as db:
        item = Household(house_number=house_number.strip(), owner_name=owner.strip(),
                         tenant_name=tenant.strip(), phone=phone.strip(), location=location.strip())
        db.add(item)
        db.commit()
        return item.id

def add_meter(serial, meter_type, household_id=None):
    with SessionLocal() as db:
        item = Meter(serial_number=serial.strip(), meter_type=meter_type,
                     household_id=household_id if household_id else None)
        db.add(item)
        db.commit()
        return item.id

def set_price(amount, effective_from):
    amount = money(amount)
    if amount <= 0:
        raise ValueError("Water price must be greater than zero.")
    with SessionLocal() as db:
        db.add(WaterPrice(price_per_m3=amount, effective_from=effective_from))
        db.commit()

def get_price(period_date):
    with SessionLocal() as db:
        row = db.scalars(select(WaterPrice).where(WaterPrice.effective_from <= period_date)
                         .order_by(WaterPrice.effective_from.desc()).limit(1)).first()
        if not row:
            raise ValueError("Set a water price effective on or before this billing period.")
        return Decimal(row.price_per_m3)

def record_reading(meter_id, period, previous, current, recorded_by="Administrator"):
    previous, current = Decimal(previous), Decimal(current)
    if current < previous:
        raise ValueError("Current reading cannot be lower than previous reading. Record a meter replacement/reset first.")
    consumption = current - previous
    with SessionLocal() as db:
        row = Reading(meter_id=meter_id, period=period, previous_value=previous,
                      current_value=current, consumption=consumption, recorded_by=recorded_by)
        db.add(row)
        db.commit()
        audit(recorded_by, "READING_RECORDED", "Reading", row.id,
              f"Meter {meter_id}; period {period}; {previous} to {current}; consumption {consumption} m3")
        return consumption

def generate_bill(household_id, period, period_date, due_date=None):
    with SessionLocal() as db:
        household = db.get(Household, household_id)
        if not household or not household.active:
            raise ValueError("Active household not found.")
        period_record = db.query(BillingPeriod).filter(BillingPeriod.name == period).first()
        if not period_record:
            raise ValueError("Create the custom billing period before generating bills.")
        if not (period_record.start_date <= period_date <= period_record.end_date):
            raise ValueError("The selected effective date must fall within the custom billing period.")
        if due_date and due_date != period_record.due_date:
            raise ValueError("The bill due date is controlled by the saved custom billing period.")
        if period_record.status != "Open":
            raise ValueError("This billing period is closed.")
        existing = db.scalars(select(Bill).where(Bill.household_id == household_id,
                                                  Bill.period == period)).first()
        if existing:
            raise ValueError("A bill already exists for this household and period.")
        meters = db.scalars(select(Meter).where(Meter.household_id == household_id,
                                                Meter.active.is_(True))).all()
        if not meters:
            raise ValueError("No active submeter is registered for this household.")
        readings = db.scalars(select(Reading).where(Reading.meter_id.in_([m.id for m in meters]),
                                                     Reading.period == period,
                                                     Reading.approved.is_(True))).all()
        if len(readings) != len(meters):
            raise ValueError("Every active household meter needs an approved reading.")
        consumption = sum((Decimal(r.consumption) for r in readings), Decimal("0"))
        price = get_price(period_date)
        water_charge = money(consumption * price)
        prior = db.scalars(select(Bill).where(Bill.household_id == household_id)
                           .order_by(Bill.created_at.desc(), Bill.id.desc())).first()
        arrears = Decimal("0")
        if prior:
            allocations = db.scalars(select(PaymentAllocation).where(PaymentAllocation.bill_id == prior.id)).all()
            if allocations:
                paid = sum((Decimal(row.amount) for row in allocations
                            if (parent := db.get(Payment, row.payment_id)) and not parent.reversed), Decimal("0"))
            else:
                paid = sum((Decimal(x.amount) for x in db.scalars(select(Payment).where(
                    Payment.bill_id == prior.id, Payment.reversed.is_(False))).all()), Decimal("0"))
            arrears = max(Decimal(prior.total_due) - paid, Decimal("0"))
        total = money(water_charge + arrears)
        bill = Bill(bill_number=f"NWM-{period.replace('-', '')}-{household_id:04d}",
                    household_id=household_id, period=period, consumption=consumption,
                    unit_price=price, water_charge=water_charge, arrears=money(arrears),
                    total_due=total, due_date=period_record.due_date, status="Unpaid")
        db.add(bill)
        db.flush()
        db.add(AuditLog(username="Administrator", action="BILL_GENERATED", entity_type="Bill",
                        entity_id=str(bill.id), details=f"{bill.bill_number}; due {bill.due_date}; total KES {total}"))
        db.commit()
        return bill.bill_number

def record_payment(bill_id, amount, method, reference, paid_on, username="Administrator"):
    amount = money(amount)
    if amount <= 0:
        raise ValueError("Payment must be greater than zero.")
    with SessionLocal() as db:
        bill = db.get(Bill, bill_id)
        if not bill:
            raise ValueError("Bill not found.")
        paid = sum((Decimal(p.amount) for p in db.scalars(select(Payment).where(
            Payment.bill_id == bill_id, Payment.reversed.is_(False))).all()), Decimal("0"))
        remaining = max(Decimal(bill.total_due) - paid, Decimal("0"))
        if amount > remaining:
            raise ValueError(f"Payment exceeds the outstanding bill balance of KES {remaining:.2f}.")
        payment = Payment(bill_id=bill_id, amount=amount, method=method,
                          reference=reference.strip(), paid_on=paid_on, recorded_by=username)
        db.add(payment)
        db.flush()
        bill.status = "Paid" if paid + amount >= Decimal(bill.total_due) else "Partially paid"
        db.add(AuditLog(username=username, action="PAYMENT_RECORDED", entity_type="Payment",
                        entity_id=str(payment.id), details=f"Bill {bill_id}; KES {amount}; {method}; reference {reference}"))
        db.commit()
        return payment.id


def save_reconciliation(period, main, sub, method, notes=""):
    main, sub = Decimal(main), Decimal(sub)
    diff = main - sub
    if diff < 0:
        raise ValueError("Submeter total exceeds the main meter. Investigate before approval.")
    with SessionLocal() as db:
        db.add(Reconciliation(period=period, main_consumption=main,
                              submeter_consumption=sub, difference=diff,
                              method=method, notes=notes))
        db.commit()
        return diff

def dashboard_summary():
    with SessionLocal() as db:
        households = db.scalar(select(func.count(Household.id)).where(Household.active.is_(True))) or 0
        bills = db.scalars(select(Bill).order_by(Bill.created_at, Bill.id)).all()
        paid = Decimal("0")
        latest = {}
        for bill in bills:
            latest[bill.household_id] = bill
            payments = db.scalars(select(Payment).where(Payment.bill_id == bill.id,
                                                        Payment.reversed.is_(False))).all()
            paid += sum((Decimal(p.amount) for p in payments), Decimal("0"))
        billed = sum((Decimal(b.water_charge) for b in bills), Decimal("0"))
        outstanding = Decimal("0")
        for bill in latest.values():
            bill_paid = sum((Decimal(p.amount) for p in db.scalars(select(Payment).where(
                Payment.bill_id == bill.id, Payment.reversed.is_(False))).all()), Decimal("0"))
            outstanding += max(Decimal(bill.total_due) - bill_paid, Decimal("0"))
        return {"households": households, "billed": money(billed), "paid": money(paid),
                "outstanding": money(outstanding)}


def audit(username, action, entity_type, entity_id="", details=""):
    with SessionLocal() as db:
        db.add(AuditLog(username=username, action=action, entity_type=entity_type,
                        entity_id=str(entity_id), details=details))
        db.commit()

def create_billing_period(name, start_date, end_date, due_date):
    if end_date < start_date:
        raise ValueError("Billing period end date cannot be before its start date.")
    if due_date <= end_date:
        raise ValueError("Payment due date must be after the billing period ends.")
    with SessionLocal() as db:
        overlap = db.query(BillingPeriod).filter(
            BillingPeriod.start_date <= end_date,
            BillingPeriod.end_date >= start_date
        ).first()
        if overlap:
            raise ValueError(f"This period overlaps with existing period {overlap.name}.")
        item = BillingPeriod(name=name, start_date=start_date, end_date=end_date, due_date=due_date)
        db.add(item)
        db.commit()
        audit("Administrator", "CREATE", "BillingPeriod", item.id,
              f"{name}: {start_date} to {end_date}; due {due_date}")
        return item.id

def get_billing_period(name):
    with SessionLocal() as db:
        period = db.query(BillingPeriod).filter(BillingPeriod.name == name).first()
        if not period:
            raise ValueError("Create the custom billing period before generating bills.")
        return period

def update_bill_status(bill_id):
    with SessionLocal() as db:
        bill = db.get(Bill, bill_id)
        if not bill:
            raise ValueError("Bill not found.")
        payments = db.query(Payment).filter(
            Payment.bill_id == bill_id, Payment.reversed.is_(False)
        ).all()
        paid = sum((Decimal(p.amount) for p in payments), Decimal("0"))
        if paid >= Decimal(bill.total_due):
            bill.status = "Paid"
        elif paid > 0:
            bill.status = "Partially paid"
        elif bill.due_date and bill.due_date < date.today():
            bill.status = "Overdue"
        else:
            bill.status = "Unpaid"
        db.commit()
        return bill.status

def record_audited_payment(bill_id, amount, method, reference, paid_on, username="Administrator"):
    return record_payment(bill_id, amount, method, reference, paid_on, username)


def replace_meter(old_meter_id, new_serial, old_final_reading, new_initial_reading,
                  replacement_date, reason, authorized_by="Administrator"):
    old_final_reading = Decimal(old_final_reading)
    new_initial_reading = Decimal(new_initial_reading)
    if not new_serial.strip():
        raise ValueError("Enter the new meter serial number.")
    with SessionLocal() as db:
        old = db.get(Meter, old_meter_id)
        if not old or not old.active:
            raise ValueError("The old meter is not active.")
        if db.query(Meter).filter(Meter.serial_number == new_serial.strip()).first():
            raise ValueError("That meter serial number is already registered.")
        previous = db.scalars(select(Reading).where(Reading.meter_id == old.id)
                              .order_by(Reading.recorded_at.desc(), Reading.id.desc()).limit(1)).first()
        if previous and old_final_reading < Decimal(previous.current_value):
            raise ValueError("The final reading cannot be below the old meter's last recorded reading.")
        new_meter = Meter(serial_number=new_serial.strip(), meter_type=old.meter_type,
                          household_id=old.household_id, active=True, installed_on=replacement_date)
        old.active = False
        db.add(new_meter)
        db.flush()
        replacement = MeterReplacement(old_meter_id=old.id, new_meter_id=new_meter.id,
            old_final_reading=old_final_reading, new_initial_reading=new_initial_reading,
            replacement_date=replacement_date, reason=reason, authorized_by=authorized_by)
        db.add(replacement)
        db.add(AuditLog(username=authorized_by, action="METER_REPLACED", entity_type="MeterReplacement",
            entity_id="", details=f"Old meter {old.serial_number}; new meter {new_serial}; final {old_final_reading}; initial {new_initial_reading}; {reason}"))
        db.commit()
        return new_meter.id

def list_audit_logs(limit=500):
    with SessionLocal() as db:
        return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()

def create_database_backup(destination):
    import shutil
    from pathlib import Path
    from config import DB_PATH
    from database import engine
    if engine.dialect.name != "sqlite":
        raise RuntimeError("File-based backup is available only for SQLite. For PostgreSQL use the pg_dump backup instructions in docs/PHASE_7.md.")
    from sqlalchemy import text
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    with engine_connect() as conn:
        conn.execute(text("PRAGMA wal_checkpoint(FULL)"))
    shutil.copy2(DB_PATH, target)
    return str(target)

def engine_connect():
    from database import engine
    return engine.connect()

def restore_database_backup(source):
    import sqlite3
    from pathlib import Path
    from config import DB_PATH
    from database import engine
    if engine.dialect.name != "sqlite":
        raise RuntimeError("SQLite restore is disabled while using PostgreSQL. Restore PostgreSQL using pg_restore as documented in docs/PHASE_7.md.")
    source = Path(source)
    if not source.is_file():
        raise ValueError("Backup file does not exist.")
    check = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    try:
        result = check.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise ValueError(f"Backup integrity check failed: {result}")
    finally:
        check.close()
    if source.resolve() == DB_PATH.resolve():
        raise ValueError("Choose a backup file, not the live database.")
    safety = DB_PATH.with_name(f"{DB_PATH.stem}_before_restore_{datetime.now():%Y%m%d_%H%M%S}.db")
    import shutil
    shutil.copy2(DB_PATH, safety)
    shutil.copy2(source, DB_PATH)
    return str(safety)

def export_bills_excel(destination):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    with SessionLocal() as db:
        rows = db.query(Bill).order_by(Bill.period, Bill.household_id).all()
        wb = Workbook()
        ws = wb.active
        ws.title = "Bills"
        ws.append(["Bill Number", "Household ID", "Period", "Consumption m3",
                   "Price per m3 (KES)", "Water Charge (KES)", "Arrears (KES)",
                   "Total Due (KES)", "Due Date", "Status"])
        for b in rows:
            ws.append([b.bill_number, b.household_id, b.period, float(b.consumption),
                       float(b.unit_price), float(b.water_charge), float(b.arrears),
                       float(b.total_due), b.due_date.isoformat() if b.due_date else "",
                       b.status or "Unpaid"])
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="087F8C")
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        wb.save(destination)
        return destination

def export_bill_pdf(bill_id, destination):
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    with SessionLocal() as db:
        bill = db.get(Bill, bill_id)
        if not bill:
            raise ValueError("Bill not found.")
        household = db.get(Household, bill.household_id)
        payments = db.query(Payment).filter(
            Payment.bill_id == bill_id, Payment.reversed.is_(False)
        ).all()
        paid = sum((Decimal(p.amount) for p in payments), Decimal("0"))
        remaining = max(Decimal(bill.total_due) - paid, Decimal("0"))
        doc = SimpleDocTemplate(destination, pagesize=A4)
        styles = getSampleStyleSheet()
        story = [Paragraph("Neighbourhood Water Management", styles["Title"]),
                 Paragraph("WATER BILL", styles["Heading2"]),
                 Spacer(1, 12)]
        data = [
            ["Bill number", bill.bill_number],
            ["Household", household.house_number if household else str(bill.household_id)],
            ["Owner", household.owner_name if household else ""],
            ["Billing period", bill.period],
            ["Consumption", f"{bill.consumption} m³"],
            ["Price per m³", f"KSh {bill.unit_price}"],
            ["Water charge", f"KSh {bill.water_charge}"],
            ["Previous arrears", f"KSh {bill.arrears}"],
            ["Total due", f"KSh {bill.total_due}"],
            ["Due date", str(bill.due_date or "Not set")],
            ["Payments received", f"KSh {paid:.2f}"],
            ["Outstanding", f"KSh {remaining:.2f}"],
        ]
        table = Table(data, colWidths=[150, 330])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#DDF5F6")),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#B9DDE0")),
            ("PADDING", (0,0), (-1,-1), 8),
        ]))
        story.append(table)
        doc.build(story)
        return destination


def _password_hash(password, salt=None):
    import hashlib, secrets, base64
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310000)
    return "pbkdf2_sha256$310000$%s$%s" % (base64.b64encode(salt).decode(), base64.b64encode(digest).decode())

def _verify_password(password, encoded):
    import hmac, base64, hashlib
    try:
        algorithm, rounds, salt_text, digest_text = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), base64.b64decode(salt_text), int(rounds))
        return hmac.compare_digest(actual, base64.b64decode(digest_text))
    except Exception:
        return False

def user_count():
    with SessionLocal() as db:
        return db.scalar(select(func.count(User.id))) or 0

def create_user(username, password, role="Administrator", actor="System"):
    username = username.strip()
    role = role.strip().title()
    if len(username) < 3:
        raise ValueError("Username must contain at least 3 characters.")
    if len(password) < 10:
        raise ValueError("Password must contain at least 10 characters.")
    if role not in ("Administrator", "Operator", "Viewer"):
        raise ValueError("Role must be Administrator, Operator or Viewer.")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.username == username)):
            raise ValueError("That username already exists.")
        user = User(username=username, password_hash=_password_hash(password), role=role)
        db.add(user)
        db.flush()
        db.add(AuditLog(username=actor, action="USER_CREATED", entity_type="User", entity_id=str(user.id), details=f"Created {role} account {username}"))
        db.commit()
        return user.id

def authenticate_user(username, password):
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username.strip(), User.active.is_(True)))
        if not user or not _verify_password(password, user.password_hash):
            return None
        db.add(AuditLog(username=user.username, action="LOGIN_SUCCESS", entity_type="User", entity_id=str(user.id), details="Successful login"))
        db.commit()
        return {"id": user.id, "username": user.username, "role": user.role}

def change_user_password(user_id, new_password, actor):
    if len(new_password) < 10:
        raise ValueError("Password must contain at least 10 characters.")
    with SessionLocal() as db:
        user = db.get(User, user_id)
        if not user:
            raise ValueError("User not found.")
        user.password_hash = _password_hash(new_password)
        db.add(AuditLog(username=actor, action="PASSWORD_CHANGED", entity_type="User", entity_id=str(user.id), details=f"Password changed for {user.username}"))
        db.commit()

def list_users():
    with SessionLocal() as db:
        return db.scalars(select(User).order_by(User.username)).all()

def set_user_active(user_id, active, actor):
    with SessionLocal() as db:
        user = db.get(User, user_id)
        if not user:
            raise ValueError("User not found.")
        if user.role == "Administrator" and not active:
            admins = db.scalars(select(User).where(User.role == "Administrator", User.active.is_(True))).all()
            if len(admins) <= 1:
                raise ValueError("The last active administrator cannot be disabled.")
        user.active = bool(active)
        db.add(AuditLog(username=actor, action="USER_ACTIVATED" if active else "USER_DISABLED", entity_type="User", entity_id=str(user.id), details=user.username))
        db.commit()

def household_account(household_id):
    with SessionLocal() as db:
        bills = db.scalars(select(Bill).where(Bill.household_id == household_id).order_by(Bill.created_at, Bill.id)).all()
        result = []
        due_total = Decimal("0")
        paid_total = Decimal("0")
        for bill in bills:
            allocations = db.scalars(select(PaymentAllocation).where(PaymentAllocation.bill_id == bill.id)).all()
            allocated = sum((Decimal(a.amount) for a in allocations
                             if (parent := db.get(Payment, a.payment_id)) and not parent.reversed), Decimal("0"))
            if not allocations:
                allocated = sum((Decimal(p.amount) for p in db.scalars(select(Payment).where(Payment.bill_id == bill.id, Payment.reversed.is_(False))).all()), Decimal("0"))
            balance = max(Decimal(bill.total_due) - allocated, Decimal("0"))
            due_total += Decimal(bill.total_due)
            paid_total += allocated
            result.append({"bill_id": bill.id, "bill_number": bill.bill_number, "period": bill.period,
                           "total_due": money(bill.total_due), "allocated": money(allocated),
                           "balance": money(balance), "due_date": bill.due_date, "status": bill.status})
        return {"household_id": household_id, "bills": result, "total_due": money(due_total),
                "total_paid": money(paid_total), "balance": money(max(due_total-paid_total, Decimal("0")))}

def record_household_payment(household_id, amount, method, reference, paid_on, username="Administrator"):
    amount = money(amount)
    if amount <= 0:
        raise ValueError("Payment must be greater than zero.")
    with SessionLocal() as db:
        bills = db.scalars(select(Bill).where(Bill.household_id == household_id).order_by(Bill.created_at, Bill.id)).all()
        if not bills:
            raise ValueError("No bills exist for this household.")
        balances = []
        for bill in bills:
            allocations = db.scalars(select(PaymentAllocation).where(PaymentAllocation.bill_id == bill.id)).all()
            if allocations:
                paid = sum((Decimal(a.amount) for a in allocations
                            if (parent := db.get(Payment, a.payment_id)) and not parent.reversed), Decimal("0"))
            else:
                paid = sum((Decimal(p.amount) for p in db.scalars(select(Payment).where(Payment.bill_id == bill.id, Payment.reversed.is_(False))).all()), Decimal("0"))
            balances.append((bill, max(Decimal(bill.total_due)-paid, Decimal("0"))))
        account_balance = sum((balance for _, balance in balances), Decimal("0"))
        if amount > account_balance:
            raise ValueError(f"Payment exceeds household balance of KES {account_balance:.2f}.")
        first_bill = next((bill for bill, balance in balances if balance > 0), bills[-1])
        payment = Payment(bill_id=first_bill.id, amount=amount, method=method, reference=reference.strip(), paid_on=paid_on, recorded_by=username)
        db.add(payment)
        db.flush()
        remaining = amount
        affected = []
        for bill, balance in balances:
            if remaining <= 0:
                break
            applied = min(balance, remaining)
            if applied > 0:
                db.add(PaymentAllocation(payment_id=payment.id, bill_id=bill.id, amount=money(applied)))
                affected.append((bill, applied))
                remaining -= applied
        db.flush()
        for bill, _ in affected:
            rows = db.scalars(select(PaymentAllocation).where(PaymentAllocation.bill_id == bill.id)).all()
            allocated = sum((Decimal(row.amount) for row in rows), Decimal("0"))
            bill.status = "Paid" if allocated >= Decimal(bill.total_due) else "Partially paid" if allocated > 0 else "Unpaid"
        details = "; ".join(f"{bill.bill_number}: KES {value:.2f}" for bill, value in affected)
        db.add(AuditLog(username=username, action="HOUSEHOLD_PAYMENT_RECORDED", entity_type="Payment", entity_id=str(payment.id), details=f"Household {household_id}; KES {amount}; {method}; {details}"))
        db.commit()
        return payment.id


def reverse_payment(payment_id, actor, actor_role, reason):
    if not reason or not reason.strip():
        raise ValueError("A reason is required for a payment reversal.")
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == actor, User.active.is_(True)))
        if not user or user.role != "Administrator" or actor_role != user.role:
            raise PermissionError("Only an active Administrator account can reverse a payment.")
        payment = db.get(Payment, payment_id)
        if not payment:
            raise ValueError("Payment not found.")
        if payment.reversed:
            raise ValueError("This payment has already been reversed.")
        payment.reversed = True
        allocations = db.scalars(select(PaymentAllocation).where(PaymentAllocation.payment_id == payment.id)).all()
        affected_ids = {row.bill_id for row in allocations}
        if not affected_ids:
            affected_ids.add(payment.bill_id)
        for bill_id in affected_ids:
            bill = db.get(Bill, bill_id)
            if not bill:
                continue
            allocation_rows = db.scalars(select(PaymentAllocation).where(PaymentAllocation.bill_id == bill_id)).all()
            if allocation_rows:
                paid = sum((Decimal(row.amount) for row in allocation_rows
                            if not (db.get(Payment, row.payment_id) and db.get(Payment, row.payment_id).reversed)), Decimal("0"))
            else:
                paid = sum((Decimal(row.amount) for row in db.scalars(select(Payment).where(
                    Payment.bill_id == bill_id, Payment.reversed.is_(False))).all()), Decimal("0"))
            bill.status = "Paid" if paid >= Decimal(bill.total_due) else "Partially paid" if paid > 0 else "Overdue" if bill.due_date and bill.due_date < date.today() else "Unpaid"
        db.add(AuditLog(username=actor, action="PAYMENT_REVERSED", entity_type="Payment",
                        entity_id=str(payment.id), details=f"KES {payment.amount}; reason: {reason.strip()}"))
        db.commit()
        return payment.id


def export_household_statement_pdf(household_id, destination):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    with SessionLocal() as db:
        household = db.get(Household, household_id)
        if not household:
            raise ValueError("Household not found.")
        bills = db.scalars(select(Bill).where(Bill.household_id == household_id).order_by(Bill.created_at, Bill.id)).all()
        styles = getSampleStyleSheet()
        story = [Paragraph("Neighbourhood Water Management", styles["Title"]),
                 Paragraph("HOUSEHOLD ACCOUNT STATEMENT", styles["Heading2"]),
                 Paragraph(f"House: {household.house_number} | Owner: {household.owner_name or 'Not recorded'}", styles["Normal"]),
                 Spacer(1, 12)]
        data = [["Period", "Bill No.", "Total (KES)", "Paid (KES)", "Balance (KES)", "Status"]]
        total_due = Decimal("0"); total_paid = Decimal("0")
        for bill in bills:
            allocations = db.scalars(select(PaymentAllocation).where(PaymentAllocation.bill_id == bill.id)).all()
            if allocations:
                paid = sum((Decimal(a.amount) for a in allocations
                            if (p := db.get(Payment, a.payment_id)) and not p.reversed), Decimal("0"))
            else:
                paid = sum((Decimal(p.amount) for p in db.scalars(select(Payment).where(
                    Payment.bill_id == bill.id, Payment.reversed.is_(False))).all()), Decimal("0"))
            balance = max(Decimal(bill.total_due) - paid, Decimal("0"))
            total_due += Decimal(bill.total_due); total_paid += paid
            status = "Paid" if balance == 0 else "Partially paid" if paid else "Unpaid"
            data.append([bill.period, bill.bill_number, f"{Decimal(bill.total_due):.2f}",
                         f"{paid:.2f}", f"{balance:.2f}", status])
        data.append(["TOTAL", "", f"{total_due:.2f}", f"{total_paid:.2f}", f"{max(total_due-total_paid, Decimal('0')):.2f}", ""])
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#087F8C")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("GRID", (0,0), (-1,-1), .4, colors.HexColor("#B9DDE0")),
            ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#DDF5F6")),
            ("PADDING", (0,0), (-1,-1), 6),
            ("FONTSIZE", (0,0), (-1,-1), 8),
        ]))
        story.extend([table, Spacer(1, 12), Paragraph("This statement reflects records currently stored in the system.", styles["Italic"])])
        SimpleDocTemplate(destination, pagesize=A4).build(story)
    return destination


def export_financial_report_excel(destination, period=None, year=None):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter
    with SessionLocal() as db:
        bills = db.scalars(select(Bill).order_by(Bill.period, Bill.household_id)).all()
        payments = db.scalars(select(Payment).order_by(Payment.paid_on, Payment.id)).all()
        if period:
            bills = [b for b in bills if b.period == period]
            payments = [p for p in payments if p.paid_on.strftime("%Y-%m") == period]
        elif year:
            bills = [b for b in bills if b.period.startswith(str(year))]
            payments = [p for p in payments if p.paid_on.year == int(year)]
        wb = Workbook(); ws = wb.active; ws.title = "Financial Summary"
        ws.append(["Neighbourhood Water Management"])
        ws.append([f"Reporting period: {period or year or 'All records'}"])
        ws.append(["Household", "Period", "Bill Number", "Consumption (m3)", "Water Charge (KES)", "Arrears (KES)", "Total Due (KES)", "Paid (KES)", "Balance (KES)", "Status"])
        for bill in bills:
            household = db.get(Household, bill.household_id)
            allocations = db.scalars(select(PaymentAllocation).where(PaymentAllocation.bill_id == bill.id)).all()
            if allocations:
                paid = sum((Decimal(a.amount) for a in allocations
                            if (p := db.get(Payment, a.payment_id)) and not p.reversed), Decimal("0"))
            else:
                paid = sum((Decimal(p.amount) for p in db.scalars(select(Payment).where(
                    Payment.bill_id == bill.id, Payment.reversed.is_(False))).all()), Decimal("0"))
            balance = max(Decimal(bill.total_due)-paid, Decimal("0"))
            ws.append([household.house_number if household else bill.household_id, bill.period, bill.bill_number,
                       float(bill.consumption), float(bill.water_charge), float(bill.arrears),
                       float(bill.total_due), float(paid), float(balance),
                       "Paid" if balance == 0 else "Partially paid" if paid else "Unpaid"])
        pay = wb.create_sheet("Payments")
        pay.append(["Payment ID", "Date", "Household", "Bill ID", "Amount (KES)", "Method", "Reference", "Recorded By", "Reversed"])
        for item in payments:
            bill = db.get(Bill, item.bill_id); household = db.get(Household, bill.household_id) if bill else None
            pay.append([item.id, item.paid_on.isoformat(), household.house_number if household else "",
                        item.bill_id, float(item.amount), item.method, item.reference, item.recorded_by,
                        "Yes" if item.reversed else "No"])
        consumption = wb.create_sheet("Consumption")
        consumption.append(["Period", "Main meter (m3)", "Submeters (m3)", "Difference (m3)", "Reconciliation method"])
        reconciliations = db.scalars(select(Reconciliation).order_by(Reconciliation.period)).all()
        for item in reconciliations:
            if period and item.period != period: continue
            if year and not item.period.startswith(str(year)): continue
            consumption.append([item.period, float(item.main_consumption), float(item.submeter_consumption), float(item.difference), item.method])
        for sheet in wb.worksheets:
            sheet.freeze_panes = "A4" if sheet.title == "Financial Summary" else "A2"
            sheet.auto_filter.ref = f"A3:{get_column_letter(sheet.max_column)}{sheet.max_row}" if sheet.title == "Financial Summary" else sheet.dimensions
            for cell in sheet[1 if sheet.title != "Financial Summary" else 3]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="087F8C")
            for column in sheet.columns:
                width = min(max(max(len(str(c.value or "")) for c in column) + 2, 12), 32)
                sheet.column_dimensions[get_column_letter(column[0].column)].width = width
        wb.save(destination)
    return destination
