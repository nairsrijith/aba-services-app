from app import db, login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import date
import json, random, string

@login_manager.user_loader
def load_user(user_id):
    return Employee.query.get(int(user_id))


class Activity(db.Model):
    __tablename__ = 'activities'
    activity_name = db.Column(db.String(51), primary_key=True)
    activity_category = db.Column(db.String(51), nullable=False)


class Designation(db.Model):
    __tablename__ = 'designations'
    designation = db.Column(db.String(51), primary_key=True)


class Employee(db.Model, UserMixin):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(51), nullable=False)
    lastname = db.Column(db.String(51))
    position = db.Column(db.String(51), db.ForeignKey('designations.designation'), nullable=False)
    rba_number = db.Column(db.String(25), nullable=True, unique=True)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    cell = db.Column(db.String(10), nullable=False)
    address1 = db.Column(db.String(120))
    address2 = db.Column(db.String(120))
    city = db.Column(db.String(51))
    state = db.Column(db.String(2))
    zipcode = db.Column(db.String(6))
    is_active = db.Column(db.Boolean, nullable=True, default=True)
    
    # User authentication fields
    password_hash = db.Column(db.String(200), nullable=True)
    user_type = db.Column(db.String(51), default='therapist', nullable=False)  # super, admin, supervisor, therapist
    locked_until = db.Column(db.DateTime, default=None)
    failed_attempt = db.Column(db.Integer, default=0, nullable=False)
    activation_key = db.Column(db.String(15), nullable=True, default=None)

    designation = db.relationship('Designation', backref='employees')
    pay_rates = db.relationship('PayRate', backref='employee', cascade='all, delete-orphan')

    def __init__(self, firstname, lastname, position, rba_number, email, cell, 
                 password=None, user_type='therapist', address1=None, address2=None, 
                 city=None, state=None, zipcode=None, is_active=True):
        self.firstname = firstname
        self.lastname = lastname
        self.position = position
        self.rba_number = rba_number
        self.email = email
        self.cell = cell
        self.address1 = address1
        self.address2 = address2
        self.city = city
        self.state = state
        self.zipcode = zipcode
        self.is_active = is_active
        self.user_type = user_type
        if password:
            self.set_password(password)
            
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def generate_activation_key(self):
        """Generate a random 8-character activation key"""
        # Generate a 8-character string of random digits and uppercase letters
        characters = string.ascii_uppercase + string.digits
        self.activation_key = ''.join(random.choices(characters, k=8))
        return self.activation_key
        
    @staticmethod
    def create_super_admin(email, password):
        """
        Creates a super admin employee
        """
        # Get or create Administrator designation
        admin_designation = Designation.query.filter_by(designation="Administrator").first()
        if not admin_designation:
            admin_designation = Designation(designation="Administrator")
            db.session.add(admin_designation)
            db.session.flush()

        # Create employee record with admin privileges
        super_admin = Employee(
            firstname="System",
            lastname="Administrator",
            position="Administrator",
            rba_number=None,
            email=email,
            cell='0000000000',
            password=password,
            user_type='super',
            address1='System',
            city='System',
            state='ON',
            zipcode='000000',
            is_active=True
        )
        db.session.add(super_admin)
        db.session.flush()

        # Create base pay rate
        base_payrate = PayRate(
            employee_id=super_admin.id,
            client_id=None,
            rate=0.0,
            effective_date=date.today()
        )
        db.session.add(base_payrate)
        db.session.commit()
        
        return super_admin


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
    is_active = db.Column(db.Boolean, nullable=True, default=True)

    supervisor = db.relationship('Employee', backref='clients')

    def __init__(self, firstname, lastname, dob, gender, parentname, parentemail, parentcell, address1, address2, city, state, zipcode, supervisor_id, cost_supervision=0.0, cost_therapy=0.0, is_active=True):
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
        self.is_active = is_active


class Intervention(db.Model):
    __tablename__ = 'interventions'
    id = db.Column(db.Integer, primary_key=True)
    # allow NULL for client_id to support base rates (apply to all clients)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    intervention_type = db.Column(db.String(51), db.ForeignKey('activities.activity_name') , nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    duration = db.Column(db.Float, nullable=False)  # Duration in hours
    file_names = db.Column(db.Text, nullable=True)  # Comma-separated filenames if multiple files are uploaded
    invoiced = db.Column(db.Boolean, default=False)  # Indicates if the intervention has been invoiced
    invoice_number = db.Column(db.String(25), db.ForeignKey('invoices.invoice_number'), nullable=True)  # Invoice number if invoiced
    is_paid = db.Column(db.Boolean, default=False)  # Indicates if the intervention has been paid

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

    def get_file_names(self):
        return json.loads(self.file_names or '[]')
    
    def set_file_names(self, filenames):
        self.file_names = json.dumps(filenames)

    def __init__(self, client_id, employee_id, intervention_type, date, start_time, end_time, duration, file_names, invoiced=False, invoice_number=None):
        self.client_id = client_id
        self.employee_id = employee_id
        self.intervention_type = intervention_type
        self.date = date
        self.start_time = start_time
        self.end_time = end_time
        self.duration = duration
        self.invoiced = invoiced
        self.file_names = file_names
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
    invoice_items = db.Column(db.Text, nullable=True)  # JSON snapshot of line items (rate, duration, cost, etc.)
    total_cost = db.Column(db.Float, nullable=False, default=0.0)  # Total cost of the invoice
    status = db.Column(db.String(25)) # Draft, Sent, Paid
    paid_date = db.Column(db.Date)
    payment_comments = db.Column(db.Text)

    client = db.relationship('Client', backref='invoices')

    def __init__(self, invoice_number, invoiced_date, payby_date, client_id, date_from, date_to, total_cost, status, paid_date, payment_comments, invoice_items=None):
        self.invoice_number = invoice_number
        self.invoiced_date = invoiced_date
        self.payby_date = payby_date
        self.client_id = client_id
        self.date_from = date_from
        self.date_to = date_to
        self.total_cost = total_cost  # Initialize total cost
        self.status = status
        self.paid_date = paid_date
        self.payment_comments = payment_comments
        self.invoice_items = invoice_items

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


class PayRate(db.Model):
    __tablename__ = 'payrates'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=True)  # Allow NULL for base rates
    rate = db.Column(db.Float, nullable=False)  # hourly rate
    effective_date = db.Column(db.Date, nullable=True)

    # employee relationship is now defined in Employee class with cascade delete
    client = db.relationship('Client', backref='payrates')

    def __repr__(self):
        return f"<PayRate emp={self.employee_id} client={self.client_id} rate={self.rate}>"


class PayStub(db.Model):
    __tablename__ = 'paystubs'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    generated_date = db.Column(db.Date, nullable=False)
    total_hours = db.Column(db.Float, nullable=False, default=0.0)
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    notes = db.Column(db.Text)

    employee = db.relationship('Employee', backref='paystubs')
    items = db.relationship('PayStubItem', backref='paystub', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<PayStub id={self.id} emp={self.employee_id} {self.period_start}..{self.period_end}>"


class PayStubItem(db.Model):
    __tablename__ = 'paystub_items'
    id = db.Column(db.Integer, primary_key=True)
    paystub_id = db.Column(db.Integer, db.ForeignKey('paystubs.id'), nullable=False)
    intervention_id = db.Column(db.Integer, db.ForeignKey('interventions.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    rate = db.Column(db.Float, nullable=False)
    hours = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float, nullable=False)

    intervention = db.relationship('Intervention')
    client = db.relationship('Client')

    def __repr__(self):
        return f"<PayStubItem paystub={self.paystub_id} int={self.intervention_id} amount={self.amount}>"

