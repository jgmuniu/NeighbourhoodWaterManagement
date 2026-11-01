import sys
from pathlib import Path
from PySide6.QtWidgets import QFileDialog, QInputDialog
from datetime import date
from decimal import Decimal
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QLineEdit, QFormLayout,
    QDialog, QMessageBox, QTabWidget, QComboBox, QDoubleSpinBox, QDateEdit,
    QHeaderView
)
from PySide6.QtCore import Qt, QDate
from database import initialize_database, SessionLocal
from models import Household, Meter, Bill, Payment, Reading, WaterPrice, MeterReplacement, User, Reconciliation
import services

AQUA = "#12B8C4"
DARK = "#075B68"


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Neighbourhood Water Management - Sign in")
        self.setMinimumWidth(360)
        self.user = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Sign in to continue"))
        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.username)
        layout.addWidget(self.password)
        button = QPushButton("Sign in")
        button.clicked.connect(self.login)
        layout.addWidget(button)

    def login(self):
        self.user = services.authenticate_user(self.username.text(), self.password.text())
        if self.user:
            self.accept()
        else:
            QMessageBox.warning(self, "Sign in failed", "The username or password is incorrect, or the account is disabled.")

class FirstAdminDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Create initial administrator")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.username = QLineEdit()
        self.password = QLineEdit(); self.password.setEchoMode(QLineEdit.Password)
        self.confirm = QLineEdit(); self.confirm.setEchoMode(QLineEdit.Password)
        form.addRow("Administrator username", self.username)
        form.addRow("Password (10+ characters)", self.password)
        form.addRow("Confirm password", self.confirm)
        layout.addLayout(form)
        button = QPushButton("Create administrator")
        button.clicked.connect(self.create)
        layout.addWidget(button)

    def create(self):
        if self.password.text() != self.confirm.text():
            QMessageBox.warning(self, "Password mismatch", "The passwords do not match.")
            return
        try:
            services.create_user(self.username.text(), self.password.text(), "Administrator", "Initial setup")
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Setup failed", str(exc))

class FormDialog(QDialog):
    def __init__(self, title, fields, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.values = {}
        layout = QVBoxLayout(self)
        form = QFormLayout()
        for key, label, kind in fields:
            if kind == "date":
                widget = QDateEdit()
                widget.setCalendarPopup(True)
                widget.setDate(QDate.currentDate())
            elif kind == "choice":
                widget = QComboBox()
                widget.addItems(["Main", "Submeter"])
            elif kind == "role":
                widget = QComboBox()
                widget.addItems(["Administrator", "Operator", "Viewer"])
            else:
                widget = QLineEdit()
                widget.setPlaceholderText(label)
                if kind == "password":
                    widget.setEchoMode(QLineEdit.Password)
            self.values[key] = widget
            form.addRow(label, widget)
        layout.addLayout(form)
        save = QPushButton("Save")
        save.clicked.connect(self.accept)
        layout.addWidget(save)

    def data(self):
        result = {}
        for key, widget in self.values.items():
            result[key] = widget.date().toPython() if isinstance(widget, QDateEdit) else widget.currentText() if isinstance(widget, QComboBox) else widget.text()
        return result

class MainWindow(QMainWindow):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.setWindowTitle(f"Neighbourhood Water Management — {current_user['username']} ({current_user['role']})")
        self.resize(1180, 760)
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background: #F3FBFC; color: #153D43; font-size: 13px; }}
            QPushButton {{ background: {AQUA}; color: white; border: 0; padding: 9px 15px; border-radius: 6px; font-weight: 600; }}
            QPushButton:hover {{ background: {DARK}; }}
            QLineEdit, QComboBox, QDateEdit {{ background: white; border: 1px solid #B9DDE0; padding: 7px; border-radius: 5px; }}
            QTableWidget {{ background: white; gridline-color: #DCEDEF; border: 1px solid #DCEDEF; }}
            QHeaderView::section {{ background: #DDF5F6; padding: 8px; border: 0; font-weight: 600; }}
            QTabBar::tab {{ padding: 10px 18px; background: #DDF5F6; }}
            QTabBar::tab:selected {{ background: {AQUA}; color: white; }}
        """)
        root = QWidget()
        layout = QVBoxLayout(root)
        heading = QLabel("Neighbourhood Water Management")
        heading.setStyleSheet(f"font-size: 25px; font-weight: 700; color: {DARK}; padding: 10px;")
        layout.addWidget(heading)
        self.summary = QLabel()
        self.summary.setStyleSheet("background:white;padding:14px;border-radius:8px;font-size:14px;")
        layout.addWidget(self.summary)
        tabs = QTabWidget()
        tabs.addTab(self.households_tab(), "Households")
        tabs.addTab(self.meters_tab(), "Meters")
        tabs.addTab(self.replacements_tab(), "Meter Replacement")
        tabs.addTab(self.readings_tab(), "Readings")
        tabs.addTab(self.billing_tab(), "Billing")
        tabs.addTab(self.payments_tab(), "Payments")
        tabs.addTab(self.settings_tab(), "Water Price")
        tabs.addTab(self.reconciliation_tab(), "Reconciliation")
        tabs.addTab(self.periods_tab(), "Billing Periods")
        tabs.addTab(self.tools_tab(), "Reports & Backup")
        tabs.addTab(self.audit_tab(), "Audit Trail")
        self.tabs = tabs
        if current_user["role"] == "Viewer":
            for index in range(1, tabs.count()):
                tabs.setTabEnabled(index, False)
        elif current_user["role"] == "Operator":
            for index in (6, 7, 9, 10):
                tabs.setTabEnabled(index, False)
        if current_user["role"] == "Administrator":
            manage = QPushButton("User Administration")
            manage.clicked.connect(self.manage_users)
            layout.addWidget(manage)
        layout.addWidget(tabs)
        self.setCentralWidget(root)
        self.refresh_all()

    def table(self, headers):
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.setAlternatingRowColors(True)
        return t

    def households_tab(self):
        w = QWidget(); l = QVBoxLayout(w)
        bar = QHBoxLayout(); add = QPushButton("Add household"); add.clicked.connect(self.add_household)
        refresh = QPushButton("Refresh"); refresh.clicked.connect(self.refresh_all)
        bar.addWidget(add); bar.addWidget(refresh); bar.addStretch()
        l.addLayout(bar)
        self.house_table = self.table(["ID", "House", "Owner", "Tenant", "Phone", "Location", "Status"])
        l.addWidget(self.house_table)
        return w

    def meters_tab(self):
        w = QWidget(); l = QVBoxLayout(w)
        bar = QHBoxLayout(); add = QPushButton("Add meter"); add.clicked.connect(self.add_meter)
        bar.addWidget(add); bar.addStretch(); l.addLayout(bar)
        self.meter_table = self.table(["ID", "Serial", "Type", "Household ID", "Status"])
        l.addWidget(self.meter_table)
        return w

    def replacements_tab(self):
        w = QWidget(); l = QVBoxLayout(w)
        form = QFormLayout()
        self.replace_old = QLineEdit(); self.replace_serial = QLineEdit()
        self.replace_final = QLineEdit(); self.replace_initial = QLineEdit()
        self.replace_date = QDateEdit(); self.replace_date.setCalendarPopup(True); self.replace_date.setDate(QDate.currentDate())
        self.replace_reason = QLineEdit()
        form.addRow("Old meter ID", self.replace_old)
        form.addRow("New meter serial number", self.replace_serial)
        form.addRow("Old meter final reading", self.replace_final)
        form.addRow("New meter initial reading", self.replace_initial)
        form.addRow("Replacement date", self.replace_date)
        form.addRow("Reason", self.replace_reason)
        l.addLayout(form)
        b = QPushButton("Authorize and record replacement")
        b.clicked.connect(self.add_replacement); l.addWidget(b)
        l.addWidget(QLabel("Replacement preserves the old meter and its readings; the new meter becomes active."))
        self.replacement_table = self.table(["Date", "Old meter ID", "New meter ID", "Old final", "New initial", "Reason", "Authorized by"])
        l.addWidget(self.replacement_table)
        return w

    def readings_tab(self):
        w = QWidget(); l = QVBoxLayout(w)
        form = QFormLayout()
        self.read_meter = QLineEdit(); self.read_period = QLineEdit(date.today().strftime("%Y-%m"))
        self.read_previous = QLineEdit(); self.read_current = QLineEdit()
        form.addRow("Meter ID", self.read_meter); form.addRow("Billing period (YYYY-MM)", self.read_period)
        form.addRow("Previous reading", self.read_previous); form.addRow("Current reading", self.read_current)
        l.addLayout(form)
        b = QPushButton("Save reading"); b.clicked.connect(self.add_reading); l.addWidget(b)
        self.read_table = self.table(["Period", "Meter ID", "Previous", "Current", "Consumption", "Recorded"])
        l.addWidget(self.read_table)
        return w

    def billing_tab(self):
        w = QWidget(); l = QVBoxLayout(w)
        form = QFormLayout()
        self.bill_house = QLineEdit(); self.bill_period = QLineEdit(date.today().strftime("%Y-%m"))
        self.bill_date = QDateEdit(); self.bill_date.setCalendarPopup(True); self.bill_date.setDate(QDate.currentDate())
        form.addRow("Household ID", self.bill_house); form.addRow("Period (YYYY-MM)", self.bill_period)
        form.addRow("Period effective date", self.bill_date)
        l.addLayout(form)
        b = QPushButton("Generate bill"); b.clicked.connect(self.generate_bill); l.addWidget(b)
        self.bill_table = self.table(["ID", "Bill No.", "Household", "Period", "Consumption", "Price/m³", "Arrears", "Total", "Due date", "Status"])
        l.addWidget(self.bill_table)
        return w

    def payments_tab(self):
        w = QWidget(); l = QVBoxLayout(w)
        form = QFormLayout()
        self.pay_bill = QLineEdit(); self.pay_amount = QLineEdit()
        self.pay_method = QComboBox(); self.pay_method.addItems(["M-Pesa", "Cash", "Bank transfer", "Other"])
        self.pay_ref = QLineEdit()
        form.addRow("Household ID", self.pay_bill); form.addRow("Amount (KES)", self.pay_amount)
        form.addRow("Method", self.pay_method); form.addRow("Transaction reference", self.pay_ref)
        l.addLayout(form)
        b = QPushButton("Record payment"); b.clicked.connect(self.add_payment); l.addWidget(b)
        l.addWidget(QLabel("Household payments are allocated to the oldest outstanding bills first."))
        self.payment_table = self.table(["ID", "Bill ID", "Amount", "Method", "Reference", "Date"])
        l.addWidget(self.payment_table)
        return w

    def settings_tab(self):
        w = QWidget(); l = QVBoxLayout(w)
        form = QFormLayout()
        self.price_amount = QLineEdit()
        self.price_date = QDateEdit(); self.price_date.setCalendarPopup(True); self.price_date.setDate(QDate.currentDate())
        form.addRow("Price per m³ (KES)", self.price_amount); form.addRow("Effective from", self.price_date)
        l.addLayout(form)
        b = QPushButton("Save water price"); b.clicked.connect(self.add_price); l.addWidget(b)
        self.price_table = self.table(["ID", "KES per m³", "Effective from"])
        l.addWidget(self.price_table)
        return w

    def reconciliation_tab(self):
        w = QWidget(); l = QVBoxLayout(w)
        form = QFormLayout()
        self.rec_period = QLineEdit(date.today().strftime("%Y-%m"))
        self.rec_main = QLineEdit(); self.rec_sub = QLineEdit()
        self.rec_method = QComboBox()
        self.rec_method.addItems(["Record only", "Equal allocation", "Proportional allocation", "Manual allocation", "Operational water loss"])
        self.rec_notes = QLineEdit()
        form.addRow("Period", self.rec_period); form.addRow("Main consumption (m³)", self.rec_main)
        form.addRow("Submeter total (m³)", self.rec_sub); form.addRow("Administrator decision", self.rec_method)
        form.addRow("Notes", self.rec_notes); l.addLayout(form)
        b = QPushButton("Save reconciliation"); b.clicked.connect(self.add_reconciliation); l.addWidget(b)
        self.rec_table = self.table(["Period", "Main", "Submeters", "Difference", "Method", "Notes"])
        l.addWidget(self.rec_table)
        return w


    def periods_tab(self):
        w = QWidget(); l = QVBoxLayout(w)
        form = QFormLayout()
        self.period_name = QLineEdit(date.today().strftime("%Y-%m"))
        self.period_start = QDateEdit(); self.period_start.setCalendarPopup(True); self.period_start.setDate(QDate.currentDate().addMonths(-1))
        self.period_end = QDateEdit(); self.period_end.setCalendarPopup(True); self.period_end.setDate(QDate.currentDate())
        self.period_due = QDateEdit(); self.period_due.setCalendarPopup(True); self.period_due.setDate(QDate.currentDate().addDays(10))
        form.addRow("Period name", self.period_name)
        form.addRow("Reading start", self.period_start)
        form.addRow("Reading end", self.period_end)
        form.addRow("Payment due date", self.period_due)
        l.addLayout(form)
        b = QPushButton("Create custom billing period")
        b.clicked.connect(self.add_period); l.addWidget(b)
        self.period_table = self.table(["Name", "Start", "End", "Due date", "Status"])
        l.addWidget(self.period_table)
        return w

    def tools_tab(self):
        w = QWidget(); l = QVBoxLayout(w)
        pdf = QPushButton("Export selected bill as PDF (enter bill ID)")
        self.export_bill_id = QLineEdit(); self.export_bill_id.setPlaceholderText("Bill ID")
        pdf.clicked.connect(self.export_pdf)
        excel = QPushButton("Export all bills to Excel"); excel.clicked.connect(self.export_excel)
        self.statement_house_id = QLineEdit(); self.statement_house_id.setPlaceholderText("Household ID for statement")
        statement = QPushButton("Export household account statement PDF"); statement.clicked.connect(self.export_statement)
        self.report_period = QLineEdit(); self.report_period.setPlaceholderText("Optional period, e.g. 2026-10")
        self.report_year = QLineEdit(); self.report_year.setPlaceholderText("Optional year, e.g. 2026")
        financial = QPushButton("Export financial, payments and consumption report")
        financial.clicked.connect(self.export_financial)
        self.reverse_payment_id = QLineEdit(); self.reverse_payment_id.setPlaceholderText("Payment ID to reverse")
        self.reverse_reason = QLineEdit(); self.reverse_reason.setPlaceholderText("Reason for reversal (required)")
        reverse = QPushButton("Administrator: reverse payment"); reverse.clicked.connect(self.reverse_payment)
        backup = QPushButton("Create database backup"); backup.clicked.connect(self.backup_db)
        restore = QPushButton("Restore database backup"); restore.clicked.connect(self.restore_db)
        l.addWidget(self.export_bill_id); l.addWidget(pdf); l.addWidget(excel)
        l.addWidget(self.statement_house_id); l.addWidget(statement)
        l.addWidget(self.report_period); l.addWidget(self.report_year); l.addWidget(financial)
        if self.current_user["role"] == "Administrator":
            l.addWidget(self.reverse_payment_id); l.addWidget(self.reverse_reason); l.addWidget(reverse)
        l.addWidget(backup); l.addWidget(restore); l.addStretch()
        return w

    def audit_tab(self):
        w = QWidget(); l = QVBoxLayout(w)
        refresh = QPushButton("Refresh audit records")
        refresh.clicked.connect(self.refresh_audit)
        l.addWidget(refresh)
        self.audit_table = self.table(["Date/time", "User", "Action", "Entity", "Record ID", "Details"])
        l.addWidget(self.audit_table)
        return w

    def add_period(self):
        self.run_action(lambda: f"Created period ID: {services.create_billing_period(
            self.period_name.text().strip(), self.period_start.date().toPython(),
            self.period_end.date().toPython(), self.period_due.date().toPython())}")

    def export_pdf(self):
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Save bill PDF", "water_bill.pdf", "PDF files (*.pdf)")
            if path:
                services.export_bill_pdf(int(self.export_bill_id.text()), path)
                self.notify("Export complete", f"PDF saved to {path}")
        except Exception as exc:
            self.notify("Export failed", str(exc), True)

    def export_excel(self):
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Save bills Excel", "water_bills.xlsx", "Excel files (*.xlsx)")
            if path:
                services.export_bills_excel(path)
                self.notify("Export complete", f"Excel report saved to {path}")
        except Exception as exc:
            self.notify("Export failed", str(exc), True)

    def export_statement(self):
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Save household statement", "household_statement.pdf", "PDF files (*.pdf)")
            if path:
                services.export_household_statement_pdf(int(self.statement_house_id.text()), path)
                self.notify("Export complete", f"Statement saved to {path}")
        except Exception as exc:
            self.notify("Export failed", str(exc), True)

    def export_financial(self):
        try:
            period = self.report_period.text().strip() or None
            year_text = self.report_year.text().strip()
            year = int(year_text) if year_text else None
            if period and year:
                raise ValueError("Enter a period or a year, not both.")
            if period and (len(period) != 7 or period[4] != "-" or not period.replace("-", "").isdigit()):
                raise ValueError("Period must use YYYY-MM format.")
            if year and (year < 2000 or year > 2100):
                raise ValueError("Enter a valid year between 2000 and 2100.")
            path, _ = QFileDialog.getSaveFileName(self, "Save financial report", "water_financial_report.xlsx", "Excel files (*.xlsx)")
            if path:
                services.export_financial_report_excel(path, period=period, year=year)
                self.notify("Export complete", f"Financial report saved to {path}")
        except Exception as exc:
            self.notify("Export failed", str(exc), True)

    def reverse_payment(self):
        try:
            if self.current_user["role"] != "Administrator":
                raise PermissionError("Only an Administrator can reverse a payment.")
            payment_id = int(self.reverse_payment_id.text())
            reason = self.reverse_reason.text().strip()
            confirm = QMessageBox.question(self, "Confirm payment reversal",
                f"Reverse payment ID {payment_id}? This action will be recorded in the audit trail.")
            if confirm != QMessageBox.Yes:
                return
            services.reverse_payment(payment_id, self.current_user["username"], self.current_user["role"], reason)
            self.notify("Payment reversed", f"Payment {payment_id} was reversed and its bills recalculated.")
            self.refresh_all()
        except Exception as exc:
            self.notify("Reversal failed", str(exc), True)

    def backup_db(self):
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Save database backup", "water_management_backup.db", "SQLite database (*.db)")
            if path:
                result = services.create_database_backup(path)
                self.notify("Backup complete", f"Database backup saved to {result}")
        except Exception as exc:
            self.notify("Backup failed", str(exc), True)

    def restore_db(self):
        try:
            path, _ = QFileDialog.getOpenFileName(self, "Select database backup", "", "SQLite database (*.db)")
            if path:
                result = services.restore_database_backup(path)
                self.notify("Restore complete", f"Database restored. Previous database preserved at {result}. Restart the application.")
        except Exception as exc:
            self.notify("Restore failed", str(exc), True)

    def refresh_audit(self):
        rows = services.list_audit_logs()
        self.fill(self.audit_table, [(x.created_at, x.username, x.action, x.entity_type, x.entity_id, x.details) for x in rows])

    def notify(self, title, message, error=False):
        (QMessageBox.critical if error else QMessageBox.information)(self, title, message)

    def run_action(self, fn):
        try:
            result = fn()
            self.refresh_all()
            self.notify("Saved", str(result) if result is not None else "Record saved successfully.")
        except Exception as exc:
            self.notify("Unable to complete action", str(exc), True)

    def add_household(self):
        d = FormDialog("Register household", [
            ("house", "House number", "text"), ("owner", "Owner name", "text"),
            ("tenant", "Tenant name", "text"), ("phone", "Telephone", "text"),
            ("location", "Location / section", "text")], self)
        if d.exec():
            v = d.data()
            self.run_action(lambda: f"Household ID: {services.add_household(v['house'],v['owner'],v['tenant'],v['phone'],v['location'])}")

    def add_meter(self):
        d = FormDialog("Register meter", [
            ("serial", "Meter serial number", "text"), ("type", "Meter type", "choice"),
            ("household", "Household ID (blank for main meter)", "text")], self)
        if d.exec():
            v = d.data()
            self.run_action(lambda: f"Meter ID: {services.add_meter(v['serial'],v['type'],int(v['household']) if v['household'].strip() else None)}")

    def add_replacement(self):
        self.run_action(lambda: f"New meter ID: {services.replace_meter(int(self.replace_old.text()), self.replace_serial.text(), self.replace_final.text(), self.replace_initial.text(), self.replace_date.date().toPython(), self.replace_reason.text())}")

    def add_reading(self):
        self.run_action(lambda: f"Consumption: {services.record_reading(int(self.read_meter.text()), self.read_period.text().strip(), self.read_previous.text(), self.read_current.text())} m³")

    def generate_bill(self):
        self.run_action(lambda: f"Generated bill: {services.generate_bill(int(self.bill_house.text()), self.bill_period.text().strip(), self.bill_date.date().toPython())}")

    def add_payment(self):
        self.run_action(lambda: services.record_household_payment(int(self.pay_bill.text()), self.pay_amount.text(),
            self.pay_method.currentText(), self.pay_ref.text(), date.today(), self.current_user["username"]) or "Payment recorded and allocated to outstanding bills.")

    def manage_users(self):
        dialog = FormDialog("Create user account", [
            ("username", "Username", "text"), ("password", "Temporary password (10+ characters)", "password"),
            ("role", "Role", "role")], self)
        if dialog.exec():
            values = dialog.data()
            self.run_action(lambda: f"Created user ID: {services.create_user(values['username'], values['password'], values['role'].strip().title(), self.current_user['username'])}")

    def add_price(self):
        self.run_action(lambda: services.set_price(self.price_amount.text(), self.price_date.date().toPython()) or "Water price saved.")

    def add_reconciliation(self):
        self.run_action(lambda: f"Difference: {services.save_reconciliation(self.rec_period.text(), self.rec_main.text(), self.rec_sub.text(), self.rec_method.currentText(), self.rec_notes.text())} m³")

    def fill(self, table, rows):
        table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                table.setItem(r, c, QTableWidgetItem(str(value)))

    def refresh_all(self):
        with SessionLocal() as status_db:
            bill_ids = [row[0] for row in status_db.query(Bill.id).all()]
        for bill_id in bill_ids:
            services.update_bill_status(bill_id)
        with SessionLocal() as db:
            households = db.query(Household).order_by(Household.id).all()
            meters = db.query(Meter).order_by(Meter.id).all()
            readings = db.query(Reading).order_by(Reading.id.desc()).all()
            bills = db.query(Bill).order_by(Bill.id.desc()).all()
            payments = db.query(Payment).order_by(Payment.id.desc()).all()
            prices = db.query(WaterPrice).order_by(WaterPrice.effective_from.desc()).all()
            recs = db.query(Reconciliation).order_by(Reconciliation.id.desc()).all()
            self.fill(self.house_table, [(x.id,x.house_number,x.owner_name,x.tenant_name,x.phone,x.location,"Active" if x.active else "Inactive") for x in households])
            self.fill(self.meter_table, [(x.id,x.serial_number,x.meter_type,x.household_id or "—","Active" if x.active else "Inactive") for x in meters])
            self.fill(self.read_table, [(x.period,x.meter_id,x.previous_value,x.current_value,x.consumption,x.recorded_at.strftime("%Y-%m-%d")) for x in readings])
            self.fill(self.bill_table, [(x.id,x.bill_number,x.household_id,x.period,x.consumption,x.unit_price,x.arrears,x.total_due,x.due_date or "—",x.status) for x in bills])
            self.fill(self.payment_table, [(x.id,x.bill_id,x.amount,x.method,x.reference,x.paid_on) for x in payments])
            if hasattr(self, "replacement_table"):
                replacements = db.query(MeterReplacement).order_by(MeterReplacement.id.desc()).all()
                self.fill(self.replacement_table, [(x.replacement_date,x.old_meter_id,x.new_meter_id,x.old_final_reading,x.new_initial_reading,x.reason,x.authorized_by) for x in replacements])
            self.fill(self.price_table, [(x.id,x.price_per_m3,x.effective_from) for x in prices])
            self.fill(self.rec_table, [(x.period,x.main_consumption,x.submeter_consumption,x.difference,x.method,x.notes) for x in recs])
            if hasattr(self, "period_table"):
                periods = db.query(__import__("models").BillingPeriod).order_by(__import__("models").BillingPeriod.start_date.desc()).all()
                self.fill(self.period_table, [(x.name,x.start_date,x.end_date,x.due_date,x.status) for x in periods])
        if hasattr(self, "audit_table"):
            self.refresh_audit()
        s = services.dashboard_summary()
        self.summary.setText(f"Active households: {s['households']}     Total billed: KSh {s['billed']:,.2f}     Collected: KSh {s['paid']:,.2f}     Outstanding: KSh {s['outstanding']:,.2f}")

def main():
    initialize_database()
    app = QApplication(sys.argv)
    if services.user_count() == 0:
        setup = FirstAdminDialog()
        if setup.exec() != QDialog.Accepted:
            return
    login = LoginDialog()
    if login.exec() != QDialog.Accepted:
        return
    window = MainWindow(login.user)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
