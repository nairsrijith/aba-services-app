import os
from flask import Flask
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
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager.init_app(app)
login_manager.login_view = 'login'

from app.clients.views import clients_bp
app.register_blueprint(clients_bp, url_prefix='/clients')

from app.employees.views import employees_bp
app.register_blueprint(employees_bp, url_prefix='/employees')

from app.interventions.views import interventions_bp
app.register_blueprint(interventions_bp, url_prefix='/interventions')

from app.invoices.views import invoices_bp
app.register_blueprint(invoices_bp, url_prefix='/invoices')

from app.users.views import users_bp
app.register_blueprint(users_bp, url_prefix='/users')

from app.manage.views import manage_bp
app.register_blueprint(manage_bp, url_prefix='/manage')

from app.error_pages.handlers import error_pages
app.register_blueprint(error_pages)


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
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    # ensure upload dirs exist inside container
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['DELETE_FOLDER'], exist_ok=True)

    # initialize extensions with this app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    # register blueprints (import at runtime to avoid circular import issues)
    from app.clients.views import clients_bp
    app.register_blueprint(clients_bp, url_prefix='/clients')
    from app.employees.views import employees_bp
    app.register_blueprint(employees_bp, url_prefix='/employees')
    from app.interventions.views import interventions_bp
    app.register_blueprint(interventions_bp, url_prefix='/interventions')
    from app.invoices.views import invoices_bp
    app.register_blueprint(invoices_bp, url_prefix='/invoices')
    from app.users.views import users_bp
    app.register_blueprint(users_bp, url_prefix='/users')
    from app.manage.views import manage_bp
    app.register_blueprint(manage_bp, url_prefix='/manage')
    from app.error_pages.handlers import error_pages
    app.register_blueprint(error_pages)

    return app