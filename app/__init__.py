import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from dotenv import load_dotenv
from io import BytesIO


load_dotenv()

login_manager = LoginManager()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'my_app_super_secret_key'

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data/database.sqlite')
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
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'my_app_super_secret_key'
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data/database.sqlite')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app