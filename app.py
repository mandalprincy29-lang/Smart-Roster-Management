import os
import calendar
from datetime import date, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///roster.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

RULES = ["All Days", "Except Public Holidays", "Sundays & Holidays Off"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

class Pod(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    lead_name = db.Column(db.String(100))

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    pod_id = db.Column(db.Integer, db.ForeignKey("pod.id"))
    weekly_off = db.Column(db.String(15), default="Sunday", nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    pod = db.relationship("Pod")

class Brand(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    operating_note = db.Column(db.String(200), default="")

class Process(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(250), default="")

class BrandProcessAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    brand_id = db.Column(db.Integer, db.ForeignKey("brand.id"), nullable=False)
    process_id = db.Column(db.Integer, db.ForeignKey("process.id"), nullable=False)
    working_rule = db.Column(db.String(50), nullable=False, default="All Days")
    min_staff = db.Column(db.Integer, default=1, nullable=False)
    brand = db.relationship("Brand")
    process = db.relationship("Process")

class EmployeeAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id"), nullable=False)
    brand_process_id = db.Column(db.Integer, db.ForeignKey("brand_process_assignment.id"), nullable=False)
    employee = db.relationship("Employee")
    assignment = db.relationship("BrandProcessAssignment")

class Holiday(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    holiday_date = db.Column(db.Date, unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)

class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id"), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default="Approved", nullable=False)
    leave_type = db.Column(db.String(30), default="Leave")
    employee = db.relationship("Employee")

class CompOff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id"), nullable=False)
    comp_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default="Approved", nullable=False)
    employee = db.relationship("Employee")

class RosterEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    roster_month = db.Column(db.String(7), nullable=False)
    work_date = db.Column(db.Date, nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id"), nullable=True)
    brand_process_id = db.Column(db.Integer, db.ForeignKey("brand_process_assignment.id"), nullable=False)
    status = db.Column(db.String(20), default="Assigned", nullable=False)
    note = db.Column(db.String(250), default="")
    employee = db.relationship("Employee")
    assignment = db.relationship("BrandProcessAssignment")

def migrate_existing_database():
    """Add new columns to existing tables without deleting user data."""
    inspector = inspect(db.engine)
    additions = {
        "employee": [
            ("weekly_off", "VARCHAR(15) NOT NULL DEFAULT 'Sunday'"),
            ("active", "BOOLEAN NOT NULL DEFAULT 1")
        ],
        "brand": [("operating_note", "VARCHAR(200) DEFAULT ''")],
        "process": [("description", "VARCHAR(250) DEFAULT ''")],
        "brand_process_assignment": [
            ("working_rule", "VARCHAR(50) NOT NULL DEFAULT 'All Days'"),
            ("min_staff", "INTEGER NOT NULL DEFAULT 1")
        ]
    }
    with db.engine.begin() as conn:
        for table, columns in additions.items():
            if table in inspector.get_table_names():
                existing = {c["name"] for c in inspect(db.engine).get_columns(table)}
                for col, definition in columns:
                    if col not in existing:
                        conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{col}" {definition}'))
    db.create_all()

with app.app_context():
    db.create_all()
    migrate_existing_database()
    if Pod.query.count() == 0:
        db.session.add_all([
            Pod(name="Pod A", lead_name="Aarav Sharma"),
            Pod(name="Pod B", lead_name="Diya Patel"),
            Pod(name="Pod C", lead_name="Rohan Mehta"),
            Pod(name="Pod D", lead_name="Ananya Singh")
        ])
        db.session.commit()
    if Process.query.count() == 0:
        db.session.add_all([
            Process(name="Customer Support", description="Handling customer queries"),
            Process(name="Order Processing", description="Managing customer orders"),
            Process(name="Email Management", description="Managing emails and responses"),
            Process(name="Quality Check", description="Checking work quality"),
            Process(name="Data Entry", description="Entering and updating data")
        ])
        db.session.commit()

def parse_date(value):
    return date.fromisoformat(value)

@app.route("/")
def dashboard():
    month = request.args.get("month", date.today().strftime("%Y-%m"))
    employees = Employee.query.order_by(Employee.name).all()
    pods = Pod.query.order_by(Pod.name).all()
    brands = Brand.query.order_by(Brand.name).all()
    processes = Process.query.order_by(Process.name).all()
    assignments = BrandProcessAssignment.query.all()
    roster = RosterEntry.query.filter_by(roster_month=month).order_by(RosterEntry.work_date).all()
    holidays = Holiday.query.order_by(Holiday.holiday_date).all()
    leaves = LeaveRequest.query.order_by(LeaveRequest.start_date).all()
    return render_template("index.html", month=month, employees=employees, pods=pods,
        brands=brands, processes=processes, assignments=assignments, roster=roster,
        holidays=holidays, leaves=leaves, rules=RULES, weekdays=WEEKDAYS,
        active_count=Employee.query.filter_by(active=True).count(),
        total_brands=Brand.query.count(), total_processes=Process.query.count(),
        total_pods=Pod.query.count())

@app.post("/employee/add")
def add_employee():
    name=request.form.get("name","").strip()
    email=request.form.get("email","").strip().lower()
    pod_id=request.form.get("pod_id") or None
    weekly_off=request.form.get("weekly_off","Sunday")
    if not name or not email:
        flash("Employee name and email are required.", "error")
    elif Employee.query.filter_by(email=email).first():
        flash("That email is already registered.", "error")
    else:
        db.session.add(Employee(name=name,email=email,pod_id=int(pod_id) if pod_id else None,weekly_off=weekly_off))
        db.session.commit(); flash("Employee added.", "success")
    return redirect(url_for("dashboard"))

@app.post("/brand/add")
def add_brand():
    name=request.form.get("name","").strip()
    if name and not Brand.query.filter(db.func.lower(Brand.name)==name.lower()).first():
        db.session.add(Brand(name=name,operating_note=request.form.get("operating_note","").strip()))
        db.session.commit(); flash("Brand added.", "success")
    else: flash("Enter a new brand name.", "error")
    return redirect(url_for("dashboard"))

@app.post("/process/add")
def add_process():
    name=request.form.get("name","").strip()
    if name and not Process.query.filter(db.func.lower(Process.name)==name.lower()).first():
        db.session.add(Process(name=name,description=request.form.get("description","").strip()))
        db.session.commit(); flash("Process added.", "success")
    else: flash("Enter a new process name.", "error")
    return redirect(url_for("dashboard"))

@app.post("/brand-process/add")
def add_brand_process():
    try:
        brand_id=int(request.form["brand_id"]); process_id=int(request.form["process_id"])
        minimum=max(1,int(request.form.get("min_staff",1)))
        rule=request.form["working_rule"]
        if rule not in RULES: raise ValueError()
        exists=BrandProcessAssignment.query.filter_by(brand_id=brand_id,process_id=process_id).first()
        if exists:
            exists.working_rule=rule; exists.min_staff=minimum
            flash("Existing brand-process rule updated.", "success")
        else:
            db.session.add(BrandProcessAssignment(brand_id=brand_id,process_id=process_id,working_rule=rule,min_staff=minimum))
            db.session.flush()
            # Do not auto-assign staff: employee eligibility is an explicit decision.
            flash("Brand-process rule added. Assign employees to it below.", "success")
        db.session.commit()
    except (ValueError, KeyError):
        db.session.rollback(); flash("Please check the assignment details.", "error")
    return redirect(url_for("dashboard"))

@app.post("/employee-assignment/add")
def add_employee_assignment():
    try:
        employee_id=int(request.form["employee_id"]); bp_id=int(request.form["brand_process_id"])
        exists=EmployeeAssignment.query.filter_by(employee_id=employee_id,brand_process_id=bp_id).first()
        if exists: flash("That employee is already assigned to this process.", "error")
        else:
            db.session.add(EmployeeAssignment(employee_id=employee_id,brand_process_id=bp_id))
            db.session.commit(); flash("Employee assigned to brand/process.", "success")
    except (ValueError, KeyError):
        flash("Choose an employee and a brand/process.", "error")
    return redirect(url_for("dashboard"))
@app.route("/employee-assignment/auto-demo")
def auto_assign_demo():
    employees = Employee.query.filter_by(active=True).order_by(Employee.id).all()
    brand_processes = BrandProcessAssignment.query.order_by(
        BrandProcessAssignment.id
    ).all()

    if not employees or not brand_processes:
        flash("Add employees and brand-process rules first.", "error")
        return redirect(url_for("dashboard"))

    added = 0
    loads = {emp.id: 0 for emp in employees}

    existing_links = EmployeeAssignment.query.all()

    for link in existing_links:
        if link.employee_id in loads:
            loads[link.employee_id] += 1

    for bp in brand_processes:
        current = EmployeeAssignment.query.filter_by(
            brand_process_id=bp.id
        ).all()

        already_assigned = {link.employee_id for link in current}
        needed = max(0, bp.min_staff - len(already_assigned))

        for _ in range(needed):
            candidates = [
                emp for emp in employees
                if emp.id not in already_assigned
            ]

            if not candidates:
                break

            chosen = min(
                candidates,
                key=lambda emp: (loads[emp.id], emp.id)
            )

            db.session.add(EmployeeAssignment(
                employee_id=chosen.id,
                brand_process_id=bp.id
            ))

            already_assigned.add(chosen.id)
            loads[chosen.id] += 1
            added += 1

    db.session.commit()

    flash(
        f"Automatic eligibility completed: {added} mappings added. "
        "Existing assignments were preserved.",
        "success"
    )

    return redirect(url_for("dashboard"))
@app.post("/holiday/add")
def add_holiday():
    try:
        d=parse_date(request.form["holiday_date"]); name=request.form.get("name","").strip()
        if not name: raise ValueError()
        if Holiday.query.filter_by(holiday_date=d).first():
            flash("A holiday already exists on that date.", "error")
        else:
            db.session.add(Holiday(holiday_date=d,name=name)); db.session.commit(); flash("Holiday added.", "success")
    except (ValueError, KeyError):
        flash("Enter a valid date and holiday name.", "error")
    return redirect(url_for("dashboard"))

@app.post("/leave/add")
def add_leave():
    try:
        eid=int(request.form["employee_id"]); start=parse_date(request.form["start_date"]); end=parse_date(request.form["end_date"])
        if end < start: raise ValueError()
        db.session.add(LeaveRequest(employee_id=eid,start_date=start,end_date=end,status="Approved",leave_type=request.form.get("leave_type","Leave")))
        db.session.commit(); flash("Approved leave added to the schedule.", "success")
    except (ValueError, KeyError):
        flash("Check the employee and leave dates.", "error")
    return redirect(url_for("dashboard"))

@app.post("/compoff/add")
def add_compoff():
    try:
        eid=int(request.form["employee_id"]); d=parse_date(request.form["comp_date"])
        db.session.add(CompOff(employee_id=eid,comp_date=d,status="Approved"))
        db.session.commit(); flash("Approved comp-off added.", "success")
    except (ValueError, KeyError):
        flash("Check the employee and comp-off date.", "error")
    return redirect(url_for("dashboard"))

def is_operating(assignment, day, holiday_dates):
    rule=assignment.working_rule
    if rule == "Sundays & Holidays Off" and (day.weekday()==6 or day in holiday_dates):
        return False
    if rule == "Except Public Holidays" and day in holiday_dates:
        return False
    return True

def unavailable_reason(employee, day, holiday_dates):
    if not employee.active: return "Inactive employee"
    if employee.weekly_off == WEEKDAYS[day.weekday()]: return "Weekly off"
    if day in holiday_dates: 
        # A public holiday does not automatically make an employee unavailable;
        # the brand/process operating rule decides whether the process runs.
        pass
    leave=LeaveRequest.query.filter(
        LeaveRequest.employee_id==employee.id,
        LeaveRequest.status=="Approved",
        LeaveRequest.start_date<=day,
        LeaveRequest.end_date>=day).first()
    if leave: return "Approved leave"
    comp=CompOff.query.filter_by(employee_id=employee.id,comp_date=day,status="Approved").first()
    if comp: return "Approved comp-off"
    return None

@app.post("/roster/generate")
def generate_roster():
    month=request.form.get("month",date.today().strftime("%Y-%m"))
    try:
        year,mon=map(int,month.split("-"))
        first=date(year,mon,1); last=date(year,mon,calendar.monthrange(year,mon)[1])
    except Exception:
        flash("Choose a valid month.", "error"); return redirect(url_for("dashboard"))
    RosterEntry.query.filter_by(roster_month=month).delete()
    db.session.commit()
    holiday_dates={h.holiday_date for h in Holiday.query.filter(Holiday.holiday_date>=first,Holiday.holiday_date<=last).all()}
    employee_ids_by_bp={}
    for link in EmployeeAssignment.query.all():
        employee_ids_by_bp.setdefault(link.brand_process_id,[]).append(link.employee_id)
    assignments=BrandProcessAssignment.query.all()
    created=0; gaps=0
    for assignment in assignments:
        eligible_ids=employee_ids_by_bp.get(assignment.id,[])
        for offset in range((last-first).days+1):
            day=first+timedelta(days=offset)
            if not is_operating(assignment,day,holiday_dates): continue
            already_used=set()
            chosen=0
            for eid in eligible_ids:
                emp=db.session.get(Employee,eid)
                if not emp or unavailable_reason(emp,day,holiday_dates): continue
                # One scheduled process per employee per day prevents same-day overlap.
                if eid in already_used: continue
                if RosterEntry.query.filter_by(roster_month=month,work_date=day,employee_id=eid).first():
                    continue
                db.session.add(RosterEntry(roster_month=month,work_date=day,employee_id=eid,
                    brand_process_id=assignment.id,status="Assigned"))
                already_used.add(eid); chosen+=1; created+=1
                if chosen>=assignment.min_staff: break
            if chosen<assignment.min_staff:
                missing=assignment.min_staff-chosen; gaps+=missing
                db.session.add(RosterEntry(roster_month=month,work_date=day,employee_id=None,
                    brand_process_id=assignment.id,status="GAP",
                    note=f"Needs {missing} more staff; no eligible employee available."))
                # GAP rows are explicitly marked and not treated as valid assignments.
    db.session.commit()
    flash(f"Roster generated for {month}: {created} staff assignments; {gaps} staffing gaps flagged.", "success" if gaps==0 else "error")
    return redirect(url_for("dashboard",month=month))

@app.post("/roster/update/<int:entry_id>")
def update_roster(entry_id):
    entry=db.session.get(RosterEntry,entry_id)
    if not entry: flash("Roster row not found.", "error"); return redirect(url_for("dashboard"))
    try:
        eid=int(request.form["employee_id"]); day=entry.work_date
        emp=db.session.get(Employee,eid)
        if not emp or unavailable_reason(emp,day,set()): raise ValueError()
        conflict=RosterEntry.query.filter(RosterEntry.work_date==day,RosterEntry.employee_id==eid,
            RosterEntry.id!=entry.id,RosterEntry.status=="Assigned").first()
        if conflict: raise ValueError()
        entry.employee_id=eid; entry.status="Assigned"; entry.note="Manually updated; review coverage."
        db.session.commit(); flash("Roster row updated. Review coverage and conflicts.", "success")
    except (ValueError, KeyError):
        db.session.rollback(); flash("That employee is unavailable or already assigned on this date.", "error")
    return redirect(url_for("dashboard",month=entry.roster_month))

@app.post("/demo/load")
def load_demo():
    # Adds fictional data only when requested; never overwrites existing records.
    if Employee.query.count() < 30:
        pods=Pod.query.all()
        for i in range(Employee.query.count()+1,31):
            email=f"demo.employee{i:02d}@example.com"
            if not Employee.query.filter_by(email=email).first():
                db.session.add(Employee(name=f"Demo Employee {i:02d}",email=email,
                    pod_id=pods[(i-1)%len(pods)].id if pods else None,
                    weekly_off=WEEKDAYS[(i-1)%7]))
        db.session.commit()
    brands=Brand.query.all()
    if Brand.query.count()==0:
        for name in ["Brand Alpha","Brand Beta","Brand Gamma","Brand Delta","Brand Epsilon"]:
            db.session.add(Brand(name=name))
        db.session.commit()
    processes=Process.query.all()
    if BrandProcessAssignment.query.count()==0 and brands and processes:
        for i,b in enumerate(brands):
            for j,p in enumerate(processes[:2]):
                db.session.add(BrandProcessAssignment(brand_id=b.id,process_id=p.id,
                    working_rule=RULES[(i+j)%3],min_staff=1 if i%4==0 else 2))
        db.session.commit()
    if EmployeeAssignment.query.count()==0:
        bps=BrandProcessAssignment.query.all(); emps=Employee.query.filter_by(active=True).all()
        for idx,bp in enumerate(bps):
            # 80% one primary person, remaining assignments get 2-3 employees.
            count=1 if idx % 5 < 4 else 3
            for emp in emps[idx:idx+count]:
                db.session.add(EmployeeAssignment(employee_id=emp.id,brand_process_id=bp.id))
        db.session.commit()
    flash("Fictional demo data added where missing. Existing data was kept.", "success")
    return redirect(url_for("dashboard"))

@app.post("/roster/clear")
def clear_roster():
    month=request.form.get("month","")
    RosterEntry.query.filter_by(roster_month=month).delete()
    db.session.commit(); flash("Roster entries for that month cleared.", "success")
    return redirect(url_for("dashboard",month=month))

if __name__ == "__main__":
    app.run(debug=True)
