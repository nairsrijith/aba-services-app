import os
from flask import Flask
import re
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from dotenv import load_dotenv
from io import BytesIO


load_dotenv()

login_manager = LoginManager()

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'doc', 'docm', 'dotx', 'dotm', 'xlsx', 'xls', 'xlsm', 'csv', 'odt', 'ods', 'odp', 'rtf', 'ppt', 'pptx', 'zip', 'rar'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)
app.config['SECRET_KEY'] = 'my_app_super_secret_key'


def _get_org_name():
    try:
        from app.models import AppSettings
        s = AppSettings.get()
        if s and s.org_name:
            return s.org_name
    except Exception:
        pass
    return os.environ.get('ORG_NAME', 'My Organization')


def _get_org_logo():
    try:
        from app.utils.settings_utils import get_org_settings
        settings = get_org_settings()
        # prefer embedded base64, then external URL, then file URI/path
        if settings.get('logo_b64'):
            return settings.get('logo_b64')
        if settings.get('logo_url'):
            return settings.get('logo_url')
        # prefer a web-accessible path for browser templates
        if settings.get('logo_web_path'):
            return settings.get('logo_web_path')
        # fallback to file URI (useful for server-side PDF rendering)
        if settings.get('logo_file_uri'):
            return settings.get('logo_file_uri')
    except Exception:
        pass
    try:
        from flask import url_for
        return url_for('static', filename='images/logo.png')
    except Exception:
        return '/static/images/logo.png'


# expose helpers to templates so they always reflect DB values regardless
app.jinja_env.globals['current_org_name'] = _get_org_name
app.jinja_env.globals['current_org_logo'] = _get_org_logo


# Inject organization-wide variables into every template so individual views
# don't need to pass them explicitly. This ensures `org_name`, `org_address`,
# `org_email`, `org_phone` and `payment_email` are always available.
@app.context_processor
def _inject_org_globals():
    # Prefer values stored in the database AppSettings if present, otherwise fall back to environment values
    try:
        from app.models import AppSettings
        s = AppSettings.get()
    except Exception:
        s = None

    # also include resolved logo fields for templates
    try:
        from app.utils.settings_utils import get_org_settings
        resolved = get_org_settings()
    except Exception:
        resolved = {}

    return {
        'org_name': (s.org_name if s and s.org_name else os.environ.get('ORG_NAME', 'My Organization')),
        'org_address': (s.org_address if s and s.org_address else os.environ.get('ORG_ADDRESS', 'Organization Address')),
        'org_email': (s.org_email if s and s.org_email else os.environ.get('ORG_EMAIL', 'email@org.com')),
        'org_phone': (s.org_phone if s and s.org_phone else os.environ.get('ORG_PHONE', 'Org Phone')),
        'payment_email': (s.payment_email if s and s.payment_email else os.environ.get('PAYMENT_EMAIL', 'payments@org.com')),
        'org_logo': (resolved.get('logo_b64') or resolved.get('logo_url') or resolved.get('logo_web_path') or resolved.get('logo_file_uri') or (('/' + s.logo_path) if s and s.logo_path else None)),
        'logo_b64': resolved.get('logo_b64'),
        'logo_url': resolved.get('logo_url'),
        'logo_file_uri': resolved.get('logo_file_uri'),
        'logo_web_path': resolved.get('logo_web_path'),
        # expose testing flags so templates can show a global banner when enabled
        'testing_mode': bool(s.testing_mode) if s and hasattr(s, 'testing_mode') else (os.environ.get('TESTING_MODE', '').lower() in ('1', 'true', 'yes')),
        'testing_email': (s.testing_email if s and hasattr(s, 'testing_email') and s.testing_email else os.environ.get('TESTING_EMAIL'))
    }


def _format_phone(value):
    """Format a digits-only phone number as XXX-XXX-XXXX for display.

    If the value contains exactly 10 digits, return formatted string. Otherwise
    return the original value (or empty string for falsy values).
    """
    if not value:
        return ''
    s = str(value)
    digits = re.sub(r'\D', '', s)
    if len(digits) == 10:
        return f"{digits[0:3]}-{digits[3:6]}-{digits[6:10]}"
    return s


def _format_date(value):
    """Normalize a date-like value to YYYY-MM-DD for templates.

    Accepts date/datetime objects or strings. If the value has a strftime
    method it will be used; otherwise strings are returned as-is.
    """
    if not value:
        return ''
    # datetime/date objects
    if hasattr(value, 'strftime'):
        try:
            return value.strftime('%Y-%m-%d')
        except Exception:
            return str(value)
    # strings — assume already in a reasonable format
    s = str(value)
    return s


def _format_time(value):
    """Normalize a time-like value to HH:MM for templates.

    Accepts time/datetime objects or strings. For strings that contain
    HH:MM:SS the seconds are dropped. If value has strftime, use it.
    """
    if not value:
        return ''
    if hasattr(value, 'strftime'):
        try:
            return value.strftime('%H:%M')
        except Exception:
            return str(value)
    s = str(value)
    # common patterns: HH:MM:SS or HH:MM
    import re
    m = re.match(r"^(\d{1,2}:\d{2})(:\d{2})?$", s)
    if m:
        return m.group(1)
    return s

basedir = os.path.abspath(os.path.dirname(__file__))

# --- CHANGED: prefer DATABASE_URL env var, fallback to sqlite ---
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    # optional: allow constructing from POSTGRES_* vars
    pg_user = os.environ.get('POSTGRES_USER')
    pg_pass = os.environ.get('POSTGRES_PASSWORD')
    pg_host = os.environ.get('POSTGRES_HOST', 'localhost')
    pg_port = os.environ.get('POSTGRES_PORT', '5432')
    pg_db   = os.environ.get('POSTGRES_DB')
    if pg_user and pg_pass and pg_db:
        database_url = f"postgresql+psycopg2://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
# fallback to sqlite when no DB info provided
app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///' + os.path.join(basedir, 'data/database.sqlite')
# --------------------------------------------------------------

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'data/uploads')
app.config['DELETE_FOLDER'] = os.path.join(basedir, 'data/deleted')
app.config['PROFILE_PIC_FOLDER'] = os.path.join(basedir, 'data/profile_pic')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
if not os.path.exists(app.config['PROFILE_PIC_FOLDER']):
    os.makedirs(app.config['PROFILE_PIC_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager.init_app(app)
login_manager.login_view = 'login'

# serve profile pics for module-level app (used by app.py)
@app.route('/profile_pic/<path:filename>', endpoint='profile_pic')
def _profile_pic_module(filename):
    from flask import send_from_directory, abort
    folder = app.config.get('PROFILE_PIC_FOLDER')
    if not folder:
        abort(404)
    try:
        return send_from_directory(folder, filename)
    except Exception:
        abort(404)

# Register Jinja filters on the global `app` instance
app.jinja_env.filters['format_phone'] = _format_phone
app.jinja_env.filters['format_date'] = _format_date
app.jinja_env.filters['format_time'] = _format_time


def create_app():
    """Application factory used by Flask CLI and by the container entrypoint."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'my_app_super_secret_key')

    basedir = os.path.abspath(os.path.dirname(__file__))

    # use DATABASE_URL if present, otherwise fall back to POSTGRES_* or sqlite
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        pg_user = os.environ.get('POSTGRES_USER')
        pg_pass = os.environ.get('POSTGRES_PASSWORD')
        pg_host = os.environ.get('POSTGRES_HOST', 'localhost')
        pg_port = os.environ.get('POSTGRES_PORT', '5432')
        pg_db   = os.environ.get('POSTGRES_DB')
        if pg_user and pg_pass and pg_db:
            database_url = f"postgresql+psycopg2://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///' + os.path.join(basedir, 'data/database.sqlite')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'data/uploads')
    app.config['DELETE_FOLDER'] = os.path.join(basedir, 'data/deleted')
    app.config['PROFILE_PIC_FOLDER'] = os.path.join(basedir, 'data/profile_pic')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    # ensure upload dirs exist inside container
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['DELETE_FOLDER'], exist_ok=True)
    os.makedirs(app.config['PROFILE_PIC_FOLDER'], exist_ok=True)

    # initialize extensions with this app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    # Register Jinja filter for factory-created app
    app.jinja_env.filters['format_phone'] = _format_phone
    app.jinja_env.filters['format_date'] = _format_date
    app.jinja_env.filters['format_time'] = _format_time

    # Also provide org globals for apps created via the factory
    @app.context_processor
    def _inject_org_globals_factory():
        try:
            from app.models import AppSettings
            s = AppSettings.get()
        except Exception:
            s = None

        # resolve logo fields using get_org_settings for factory-created apps
        try:
            from app.utils.settings_utils import get_org_settings
            resolved = get_org_settings()
        except Exception:
            resolved = {}

        return {
            'org_name': (s.org_name if s and s.org_name else os.environ.get('ORG_NAME', 'My Organization')),
            'org_address': (s.org_address if s and s.org_address else os.environ.get('ORG_ADDRESS', 'Organization Address')),
            'org_email': (s.org_email if s and s.org_email else os.environ.get('ORG_EMAIL', 'email@org.com')),
            'org_phone': (s.org_phone if s and s.org_phone else os.environ.get('ORG_PHONE', 'Org Phone')),
            'payment_email': (s.payment_email if s and s.payment_email else os.environ.get('PAYMENT_EMAIL', 'payments@org.com')),
            'org_logo': (resolved.get('logo_b64') or resolved.get('logo_url') or resolved.get('logo_web_path') or resolved.get('logo_file_uri') or (('/' + s.logo_path) if s and s.logo_path else None)),
            'logo_b64': resolved.get('logo_b64'),
            'logo_url': resolved.get('logo_url'),
            'logo_file_uri': resolved.get('logo_file_uri'),
            'logo_web_path': resolved.get('logo_web_path'),
            'testing_mode': bool(s.testing_mode) if s and hasattr(s, 'testing_mode') else (os.environ.get('TESTING_MODE', '').lower() in ('1', 'true', 'yes')),
            'testing_email': (s.testing_email if s and hasattr(s, 'testing_email') and s.testing_email else os.environ.get('TESTING_EMAIL'))
        }

    # Register the same helpers for factory-created app so templates can call them
    def _factory_get_org_name():
        try:
            from app.models import AppSettings
            ss = AppSettings.get()
            if ss and ss.org_name:
                return ss.org_name
        except Exception:
            pass
        return os.environ.get('ORG_NAME', 'My Organization')

    def _factory_get_org_logo():
        try:
            from app.utils.settings_utils import get_org_settings
            settings = get_org_settings()
            if settings.get('logo_b64'):
                return settings.get('logo_b64')
            if settings.get('logo_url'):
                return settings.get('logo_url')
            if settings.get('logo_web_path'):
                return settings.get('logo_web_path')
            if settings.get('logo_file_uri'):
                return settings.get('logo_file_uri')
        except Exception:
            pass
        try:
            from flask import url_for
            return url_for('static', filename='images/logo.png')
        except Exception:
            return '/static/images/logo.png'

    app.jinja_env.globals['current_org_name'] = _factory_get_org_name
    app.jinja_env.globals['current_org_logo'] = _factory_get_org_logo

    @app.route('/profile_pic/<path:filename>', endpoint='profile_pic')
    def profile_pic_factory(filename):
        from flask import send_from_directory, abort
        folder = app.config.get('PROFILE_PIC_FOLDER')
        if not folder:
            abort(404)
        try:
            return send_from_directory(folder, filename)
        except Exception:
            abort(404)

    return app


# CLI helper to initialize DB tables and ensure AppSettings exists
@app.cli.command('init-settings')
def init_settings():
    """Create DB tables (if missing) and ensure a single AppSettings row exists.

    Usage:
      flask init-settings
    """
    try:
        from app import db
        from app.models import AppSettings
        db.create_all()
        s = AppSettings.get()
        if s:
            print('AppSettings initialized or already present.')
        else:
            print('Failed to initialize AppSettings — check database/migrations.')
    except Exception as e:
        print('Error initializing settings:', e)