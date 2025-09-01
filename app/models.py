from app import db, login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
# from datetime import date


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    user_type = db.Column(db.String(51), default=None, nullable=False)
    locked = db.Column(db.Boolean, default=False, nullable=False)
    locked_until = db.Column(db.DateTime, default=None)
    failed_attempt = db.Column(db.Integer, default=0, nullable=False)
    activation_key = db.Column(db.String(15), nullable=True, default=None)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Activity(db.Model):
    __tablename__ = 'activities'
    activity_name = db.Column(db.String(51), primary_key=True)
    activity_category = db.Column(db.String(51), nullable=False)


class Designation(db.Model):
    __tablename__ = 'designations'
    designation = db.Column(db.String(51), primary_key=True)


class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(51), nullable=False)
    lastname = db.Column(db.String(51))
    position = db.Column(db.String(51), db.ForeignKey('designations.designation'), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    cell = db.Column(db.String(10), nullable=False)
    address1 = db.Column(db.String(120))
    address2 = db.Column(db.String(120))
    city = db.Column(db.String(51))
    state = db.Column(db.String(2))
    zipcode = db.Column(db.String(6))

    designation = db.relationship('Designation', backref='employees')

    def __init__(self, firstname, lastname, position, email, cell, address1=None, address2=None, city=None, state=None, zipcode=None):
        self.firstname = firstname
        self.lastname = lastname
        self.position = position
        self.email = email
        self.cell = cell
        self.address1 = address1
        self.address2 = address2
        self.city = city
        self.state = state
        self.zipcode = zipcode


class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(51), nullable=False)
    lastname = db.Column(db.String(51))
    dob = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(51), nullable=False)
    parentname = db.Column(db.String(101), nullable=False)
    parentemail = db.Column(db.String(120), nullable=False)
    parentcell = db.Column(db.String(10), nullable=False)
    address1 = db.Column(db.String(120), nullable=False)
    address2 = db.Column(db.String(120))
    city = db.Column(db.String(51), nullable=False)
    state = db.Column(db.String(2), nullable=False)
    zipcode = db.Column(db.String(6), nullable=False)
    supervisor_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    cost_supervision = db.Column(db.Float, nullable=False, default=0.0)
    cost_therapy = db.Column(db.Float, nullable=False, default=0.0)

    supervisor = db.relationship('Employee', backref='clients')

    def __init__(self, firstname, lastname, dob, gender, parentname, parentemail, parentcell, address1, address2, city, state, zipcode, supervisor_id, cost_supervision=0.0, cost_therapy=0.0):
        self.firstname = firstname
        self.lastname = lastname
        self.dob = dob
        self.gender = gender
        self.parentname = parentname
        self.parentemail = parentemail
        self.parentcell = parentcell
        self.address1 = address1
        self.address2 = address2
        self.city = city
        self.state = state
        self.zipcode = zipcode
        self.supervisor_id = supervisor_id
        self.cost_supervision = cost_supervision
        self.cost_therapy = cost_therapy


class Intervention(db.Model):
    __tablename__ = 'interventions'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    intervention_type = db.Column(db.String(51), db.ForeignKey('activities.activity_name') , nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    duration = db.Column(db.Float, nullable=False)  # Duration in hours
    invoiced = db.Column(db.Boolean, default=False)  # Indicates if the intervention has been invoiced
    invoice_number = db.Column(db.String(25), db.ForeignKey('invoices.invoice_number'), nullable=True)  # Invoice number if invoiced

    client = db.relationship('Client', backref='interventions')
    employee = db.relationship('Employee', backref='interventions')
    invoice = db.relationship('Invoice', backref='interventions')
    activity = db.relationship('Activity', backref='interventions')

    _duration = db.Column('duration', db.Float, nullable=False)  # private field

    @property
    def duration(self):
        return round(self._duration, 2) if self._duration is not None else None

    @duration.setter
    def duration(self, value):
        self._duration = round(float(value), 2) if value is not None else None


    def __init__(self, client_id, employee_id, intervention_type, date, start_time, end_time, duration, invoiced=False, invoice_number=None):
        self.client_id = client_id
        self.employee_id = employee_id
        self.intervention_type = intervention_type
        self.date = date
        self.start_time = start_time
        self.end_time = end_time
        self.duration = duration
        self.invoiced = invoiced
        self.invoice_number = invoice_number


class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(25), unique=True, nullable=False)  # Format: INVYYYYMM00000001
    invoiced_date = db.Column(db.Date, nullable=False)
    payby_date = db.Column(db.Date, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    date_from = db.Column(db.Date, nullable=False)
    date_to = db.Column(db.Date, nullable=False)
    intervention_ids = db.Column(db.String, nullable=True)  # Store as comma-separated IDs
    total_cost = db.Column(db.Float, nullable=False, default=0.0)  # Total cost of the invoice
    status = db.Column(db.String(25)) # Draft, Sent, Paid
    paid_date = db.Column(db.Date)
    payment_comments = db.Column(db.Text)

    client = db.relationship('Client', backref='invoices')

    def __init__(self, invoice_number, invoiced_date, payby_date, client_id, date_from, date_to, intervention_ids, total_cost, status, paid_date, payment_comments):
        self.invoice_number = invoice_number
        self.invoiced_date = invoiced_date
        self.payby_date = payby_date
        self.client_id = client_id
        self.date_from = date_from
        self.date_to = date_to
        self.intervention_ids = intervention_ids
        self.total_cost = total_cost  # Initialize total cost
        self.status = status
        self.paid_date = paid_date
        self.payment_comments = payment_comments

    @staticmethod
    def generate_invoice_number():
        today = date.today()
        date_str = today.strftime('%Y%m')
        # Count existing invoices for today to get the next sequence
        count = Invoice.query.filter(
            Invoice.invoice_number.like(f'INV{date_str}%')
        ).count() + 1
        seq = str(count).zfill(4)
        return f'INV{date_str}{seq}'

