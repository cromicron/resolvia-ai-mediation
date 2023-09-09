from flask import Flask
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

db = SQLAlchemy()
login = LoginManager()
login.login_view = 'auth.login'  # Tell Flask-Login which view logs users in.
migrate = Migrate()
socketio = SocketIO(cors_allowed_origins="*")

@login.user_loader
def load_user(id):
    from app.models import User  # Moved the import here to avoid potential circular imports.
    return User.query.get(int(id))

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_secret_key'  # This is required for Flask-Login.
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'site.db')

    db.init_app(app)
    login.init_app(app)
    migrate.init_app(app, db)
    # Register blueprints
    from app.main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from app.mediation import mediation_bp
    app.register_blueprint(mediation_bp)
    socketio.init_app(app, cors_allowed_origins="*")

    with app.app_context():
        db.create_all()

    return app
