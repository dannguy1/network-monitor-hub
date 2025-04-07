import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_apscheduler import APScheduler
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from cryptography.fernet import Fernet
from ..config import config

db = SQLAlchemy()
migrate = Migrate()
scheduler = APScheduler()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# --- Encryption Setup ---
def get_encryption_key():
    key = os.environ.get('ENCRYPTION_KEY')
    if not key:
        raise ValueError("ENCRYPTION_KEY environment variable not set!")
    return key.encode()

def get_cipher_suite():
    try:
        return Fernet(get_encryption_key())
    except Exception as e:
        # Provide more context if the key is invalid
        print(f"Error initializing Fernet. Ensure ENCRYPTION_KEY is a valid Fernet key. Error: {e}")
        raise ValueError("Invalid ENCRYPTION_KEY provided.") from e
# --- End Encryption Setup ---

def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'default')

    # Make sure instance path exists before initializing LoginManager if it depends on it
    instance_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'instance')
    try:
        os.makedirs(instance_path)
    except OSError:
        pass

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    limiter.init_app(app)
    if not scheduler.running:
        scheduler.init_app(app)
        scheduler.start()
        print("Scheduler started.")
    else:
        print("Scheduler already running.")

    # Setup CORS properly
    # Allow requests from the frontend origin (adjust in production)
    frontend_origin = app.config.get('FRONTEND_ORIGIN', 'http://localhost:3000')
    CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": frontend_origin}})

    # Register blueprints
    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api/v1')
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    # Import and register the new dashboard blueprint
    from .api.dashboard import bp as dashboard_bp
    app.register_blueprint(dashboard_bp, url_prefix='/api/v1/dashboard')

    # Register CLI commands (important for background tasks management)
    from . import cli
    cli.register(app)

    # Schedule tasks if needed (make sure this runs only once)
    if not app.config.get('TESTING'): # Don't run scheduler in tests easily
        # Check if the job is already scheduled to avoid duplicates on reload
        if not scheduler.get_job('push_ai_logs'):
            from .services.ai_pusher import push_logs_to_ai
            push_interval = app.config.get('AI_PUSH_INTERVAL_MINUTES', 10)
            scheduler.add_job(id='push_ai_logs', func=push_logs_to_ai,
                              trigger='interval', minutes=push_interval)
            print(f"Scheduled AI log push every {push_interval} minutes.")

    print(f"App created with config: {config_name}")
    return app 