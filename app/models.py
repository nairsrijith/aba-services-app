from app import db, login_manager
import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import date
from datetime import datetime
import json, string, secrets

@login_manager.user_loader
def load_user(user_id):
    try:
        user = Employee.query.get(int(user_id))
    except Exception:
        return None

    # If user record doesn't exist, or login is disabled, or account inactive -> treat as anonymous
    if not user:
        return None

    # If login is explicitly disabled or employee marked inactive, don't load the user
    if not getattr(user, 'login_enabled', False) or not getattr(user, 'is_active', True):
        return None

    # If account is locked until a future time, don't load
    if getattr(user, 'locked_until', None):
        try:
            if user.locked_until > datetime.utcnow():
                return None
        except Exception:
            # If locked_until is not a datetime for some reason, ignore and continue
            pass

    return user


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
    is_active = db.Column(db.Boolean, nullable=True, default=True)  # Controls if employee record is active in the system
    
    # User authentication fields
    password_hash = db.Column(db.String(200), nullable=True)
    user_type = db.Column(db.String(51), default='therapist', nullable=False)  # super, admin, supervisor, therapist
    login_enabled = db.Column(db.Boolean, nullable=False, default=False)  # Controls if user can log in
    locked_until = db.Column(db.DateTime, default=None)
    failed_attempt = db.Column(db.Integer, default=-2, nullable=False)
    activation_key = db.Column(db.String(16), nullable=True, default=None)
    # Profile picture path stored as a relative path under the project (e.g. 'data/profile_pic/filename.png')
    profile_pic = db.Column(db.String(255), nullable=True)

    designation = db.relationship('Designation', backref='employees')
    pay_rates = db.relationship('PayRate', backref='employee', cascade='all, delete-orphan')

    def __init__(self, firstname, lastname, position, rba_number, email, cell, 
                 password=None, user_type='therapist', address1=None, address2=None, 
                 city=None, state=None, zipcode=None, is_active=True, failed_attempt=-2,
                 locked_until=None, login_enabled=False):
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
        self.failed_attempt = failed_attempt
        self.locked_until = locked_until
        self.login_enabled = login_enabled
        if password:
            self.set_password(password)
            
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def generate_activation_key(self, length: int = 12, num_lowercase=3, num_uppercase=3, num_digits=3):
        """
        Generates a cryptographically secure activation key with specific character counts.

        Args:
            length (int): The total length of the key. Must be at least num_lower + num_upper + num_digits.
            num_lower (int): The minimum number of lowercase letters.
            num_upper (int): The minimum number of uppercase letters.
            num_digits (int): The minimum number of digits.

        Returns:
            str: A randomly generated activation key.
        
        Raises:
            ValueError: If the total length is too short to meet the minimum character counts.

        The method sets `self.activation_key` and returns the generated key. It does
        not commit the session — callers should commit when ready.
        """

        if length < (num_lowercase + num_uppercase + num_digits):
            raise ValueError("Total length is too short for the specified character requirements")
        
        lowercase = ''.join(secrets.choice(string.ascii_lowercase) for _ in range(num_lowercase))
        uppercase = ''.join(secrets.choice(string.ascii_uppercase) for _ in range(num_uppercase))
        digits = ''.join(secrets.choice(string.digits) for _ in range(num_digits))

        remaining_length = length - (num_lowercase + num_uppercase + num_digits)

        if remaining_length > 0:
            all_possible_characters = string.ascii_lowercase + string.ascii_uppercase + string.digits
            remaining = ''.join(secrets.choice(all_possible_characters) for _ in range(remaining_length))
            all_characters = lowercase + uppercase + digits + remaining
        else:
            all_characters = lowercase + uppercase + digits

        character_list = list(all_characters)
        secrets.SystemRandom().shuffle(character_list)

        key = ''.join(character_list)
        self.activation_key = key
        return key
        
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
            is_active=True,
            login_enabled=True
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
    parentemail2 = db.Column(db.String(120), nullable=True)
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

    def __init__(self, firstname, lastname, dob, gender, parentname, parentemail, parentemail2, parentcell, address1, address2, city, state, zipcode, supervisor_id, cost_supervision=0.0, cost_therapy=0.0, is_active=True):
        self.firstname = firstname
        self.lastname = lastname
        self.dob = dob
        self.gender = gender
        self.parentname = parentname
        self.parentemail = parentemail
        self.parentemail2 = parentemail2
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

    @classmethod
    def has_overlap(cls, employee_id, date, start_time, end_time, exclude_id=None):
        """
        Check if there's any overlapping session for the given employee at the specified time.
        
        Args:
            employee_id: The ID of the employee to check
            date: The date of the session
            start_time: The start time of the session
            end_time: The end time of the session
            exclude_id: Optional intervention ID to exclude from the check (for updates)
            
        Returns:
            bool: True if there's an overlap, False otherwise
        """
        query = cls.query.filter(
            cls.employee_id == employee_id,
            cls.date == date,
            # Check if either the start or end time falls within an existing session
            db.or_(
                # New session starts during an existing session
                db.and_(
                    cls.start_time <= start_time,
                    cls.end_time > start_time
                ),
                # New session ends during an existing session
                db.and_(
                    cls.start_time < end_time,
                    cls.end_time >= end_time
                ),
                # New session completely contains an existing session
                db.and_(
                    cls.start_time >= start_time,
                    cls.end_time <= end_time
                )
            )
        )
        
        # Exclude the current intervention if updating
        if exclude_id is not None:
            query = query.filter(cls.id != exclude_id)
            
        return query.first() is not None

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
    last_reminder_sent_date = db.Column(db.DateTime, nullable=True)  # Tracks when last reminder was sent
    reminder_count = db.Column(db.Integer, default=0)  # Tracks how many reminders have been sent

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
        self.last_reminder_sent_date = None
        self.reminder_count = 0

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
    email_sent = db.Column(db.Boolean, default=False, nullable=False)

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


class MileageRate(db.Model):
    __tablename__ = 'mileage_rates'
    id = db.Column(db.Integer, primary_key=True)
    rate = db.Column(db.Float, nullable=False)  # Rate per kilometer (e.g., 0.36 for $0.36 per km)
    effective_date = db.Column(db.Date, nullable=False)  # Date when this rate becomes effective
    created_date = db.Column(db.Date, default=date.today)  # When the rate was created

    mileages = db.relationship('Mileage', backref='mileage_rate', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<MileageRate rate=${self.rate}/km effective={self.effective_date}>"


class Mileage(db.Model):
    __tablename__ = 'mileages'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)  # Date of travel
    distance = db.Column(db.Float, nullable=False)  # Distance in kilometers
    description = db.Column(db.String(255), nullable=True)  # Optional: reason for travel (e.g., "Therapy session")
    mileage_rate_id = db.Column(db.Integer, db.ForeignKey('mileage_rates.id'), nullable=False)  # Rate used for this entry
    cost = db.Column(db.Float, nullable=False)  # Calculated cost (distance * rate)
    invoice_number = db.Column(db.String(25), db.ForeignKey('invoices.invoice_number'), nullable=True)  # Invoice number if invoiced
    invoiced = db.Column(db.Boolean, default=False)  # Indicates if included in an invoice
    is_paid = db.Column(db.Boolean, default=False)  # Indicates if included in a paystub payment

    employee = db.relationship('Employee', backref='mileages')
    client = db.relationship('Client', backref='mileages')

    def __init__(self, employee_id, client_id, date, distance, mileage_rate_id, description=None):
        self.employee_id = employee_id
        self.client_id = client_id
        self.date = date
        self.distance = distance
        self.mileage_rate_id = mileage_rate_id
        self.description = description
        # Calculate cost based on the rate
        mileage_rate = MileageRate.query.get(mileage_rate_id)
        if mileage_rate:
            self.cost = round(distance * mileage_rate.rate, 2)
        else:
            self.cost = 0.0

    def __repr__(self):
        return f"<Mileage emp={self.employee_id} client={self.client_id} date={self.date} dist={self.distance}km cost=${self.cost}>"

    @staticmethod
    def get_effective_rate(effective_date):
        """Get the mileage rate that's effective on a given date."""
        # Get the most recent rate that is on or before the effective_date
        rate = MileageRate.query.filter(
            MileageRate.effective_date <= effective_date
        ).order_by(MileageRate.effective_date.desc()).first()
        return rate


class AppSettings(db.Model):
    __tablename__ = 'app_settings'
    id = db.Column(db.Integer, primary_key=True)
    org_name = db.Column(db.String(200))
    org_address = db.Column(db.String(500))
    org_phone = db.Column(db.String(50))
    org_email = db.Column(db.String(120))
    payment_email = db.Column(db.String(120))
    logo_path = db.Column(db.String(500))

    gmail_client_id = db.Column(db.String(200))
    gmail_client_secret = db.Column(db.String(200))
    gmail_refresh_token = db.Column(db.String(200))

    testing_mode = db.Column(db.Boolean, default=False)
    testing_email = db.Column(db.String(120))
    default_cc = db.Column(db.String(120))

    # Invoice reminder settings
    invoice_reminder_enabled = db.Column(db.Boolean, default=False)
    invoice_reminder_days = db.Column(db.Integer, default=5)  # Send reminder X days before due date
    invoice_reminder_repeat_enabled = db.Column(db.Boolean, default=False)
    invoice_reminder_repeat_days = db.Column(db.Integer, default=3)  # Repeat reminder every X days

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get(cls):
        import logging
        logger = logging.getLogger(__name__)
        try:
            s = cls.query.first()
            if s:
                logger.debug(f'AppSettings retrieved from database (ID: {s.id}, invoice_reminder_enabled: {s.invoice_reminder_enabled})')
                return s

            # If no AppSettings row exists, create one from environment defaults
            logger.warning('No AppSettings row found in database, creating default from environment')
            s = cls(
                org_name=os.environ.get('ORG_NAME'),
                org_address=os.environ.get('ORG_ADDRESS'),
                org_phone=os.environ.get('ORG_PHONE'),
                org_email=os.environ.get('ORG_EMAIL'),
                payment_email=os.environ.get('PAYMENT_EMAIL'),
                logo_path=os.environ.get('LOGO_PATH'),
                testing_mode=False,
                testing_email=None,
                default_cc=None
            )
            try:
                db.session.add(s)
                db.session.commit()
                logger.info('Created default AppSettings row')
            except Exception as e:
                logger.error(f'Failed to create default AppSettings: {e}')
                db.session.rollback()
            return s
        except Exception as e:
            logger.error(f'Exception in AppSettings.get(): {e}', exc_info=True)
            return None

