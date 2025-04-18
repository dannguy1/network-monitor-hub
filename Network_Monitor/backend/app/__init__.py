import os
import logging # Import logging
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
from dotenv import load_dotenv

db = SQLAlchemy()
migrate = Migrate()
scheduler = APScheduler()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
limiter = Limiter(
    key_func=get_remote_address,
    # Set limits extremely high to avoid issues during testing
    default_limits=["10000 per day", "2000 per hour", "500 per minute"]
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
    # --- Add Debug --- #
    # logging.warning("DEBUG APP CREATE: Entered create_app function.")
    # --- End Debug --- #
    try:
        # --- Explicitly load .env VERY early --- #
        # This ensures environment variables are set before config object is loaded
        # basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) # /backend
        # Use a simpler path based on current file
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(backend_dir) # Assumes structure /project_root/backend/app
        dotenv_path = os.path.join(project_root, '..', '.env') # Try going up one level from project_root
        # Use load_dotenv directly, override ensures .env takes precedence over system env vars if needed
        loaded = load_dotenv(dotenv_path, override=True)
        # logging.warning(f"DEBUG: Attempted early load of .env from: {dotenv_path}. Loaded: {loaded}")
        # --- End early load ---

        if config_name is None:
            config_name = os.getenv('FLASK_CONFIG', 'default')
        # logging.warning(f"DEBUG APP CREATE: Using config_name = {config_name}")

        # Make sure instance path exists before initializing LoginManager if it depends on it
        instance_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'instance')
        try:
            os.makedirs(instance_path)
        except OSError:
            pass

        app = Flask(__name__, instance_relative_config=True)
        # logging.warning("DEBUG APP CREATE: Flask app object created.")

        app.config.from_object(config[config_name])
        # logging.warning("DEBUG APP CREATE: app.config.from_object completed.")

        config[config_name].init_app(app)
        # logging.warning("DEBUG APP CREATE: config[config_name].init_app(app) completed.")

        # --- FIX: Explicitly set config values AFTER load_dotenv and from_object --- #
        # Read directly from the environment *now* and ensure correct boolean type.
        # This overrides any potentially stale value copied from Config class definition.
        app.config['AI_ENGINE_ENABLED'] = str(os.environ.get('AI_ENGINE_ENABLED', 'false')).lower() == 'true'
        app.config['AI_ENGINE_MQTT_TLS_ENABLED'] = str(os.environ.get('AI_ENGINE_MQTT_TLS_ENABLED', 'false')).lower() == 'true'
        app.config['LOG_ANALYZER_MQTT_ENABLED'] = str(os.environ.get('LOG_ANALYZER_MQTT_ENABLED', 'false')).lower() == 'true'
        # Ensure other necessary values are present if not defined via os.environ in config.py
        app.config.setdefault('AI_ENGINE_MQTT_QOS', 1)
        app.config.setdefault('AI_ENGINE_MQTT_CLIENT_ID', 'network_monitor_ai_pusher')
        # --- End FIX --- #

        # Initialize extensions
        db.init_app(app)
        migrate.init_app(app, db)
        login_manager.init_app(app)
        limiter.init_app(app)

        # --- Add Debug --- #
        # logging.warning("DEBUG SCHEDULER: Before scheduler init/start block.")
        # --- End Debug --- #
        if not scheduler.running:
            scheduler.init_app(app)
            scheduler.start()
            # logging.warning("Scheduler started.") # Use logging
        # --- Add Debug --- #
        # logging.warning("DEBUG SCHEDULER: After scheduler init/start block.")
        # --- End Debug --- #
        
        # Setup CORS properly
        # --- REMOVE redundant dotenv load here --- #
        # basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) # Should be /backend
        # dotenv_path = os.path.join(basedir, '..', '.env') # Go up one more level to Network_Monitor/.env
        # load_dotenv(dotenv_path, override=True) # Override existing env vars if needed
        # print(f"DEBUG: Explicitly loaded .env from: {dotenv_path}")
        # --- End redundant load --- #

        # Allow requests from the frontend origin (adjust in production)
        # Read directly from os.environ after loading .env
        frontend_origin_env = os.environ.get('FRONTEND_ORIGIN', 'http://localhost:3000')
        # logging.warning(f"DEBUG: Configuring CORS for origin: {frontend_origin_env}")
        CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": frontend_origin_env}})

        # Register blueprints
        from .api import api as api_blueprint
        app.register_blueprint(api_blueprint, url_prefix='/api/v1')

        # Register auth blueprint under /api/v1 as well
        from .auth import auth as auth_blueprint
        app.register_blueprint(auth_blueprint, url_prefix='/api/v1/auth')

        # Import and register the new dashboard blueprint
        from .api.dashboard import bp as dashboard_bp
        app.register_blueprint(dashboard_bp, url_prefix='/api/v1/dashboard')

        # Import and register the new UCI blueprint
        from .api.uci import bp as uci_bp
        app.register_blueprint(uci_bp, url_prefix='/api/v1/uci')

        # Register CLI commands (important for background tasks management)
        from . import cli
        cli.register(app)

        # Schedule tasks if needed (make sure this runs only once)
        # --- Add Debug Prints --- #
        # print(f"DEBUG SCHEDULER CHECK: TESTING = {app.config.get('TESTING')}, AI_ENABLED = {app.config.get('AI_ENGINE_ENABLED')}")
        # --- End Debug Prints --- #
        # logging.warning(f"DEBUG SCHEDULER: Config Name = {config_name}")
        testing_value = app.config.get('TESTING')
        # logging.warning(f"DEBUG SCHEDULER: Value of app.config.get('TESTING') = {testing_value} (Type: {type(testing_value)})")

        if not testing_value: # Don't run scheduler in tests easily
            # logging.warning("DEBUG SCHEDULER: Entered 'if not testing_value' block.") # Check if block is entered
            ai_enabled = app.config.get('AI_ENGINE_ENABLED') # Read the *converted* boolean value
            # logging.warning(f"DEBUG SCHEDULER: Inner check AI_ENABLED = {ai_enabled}")

            if ai_enabled:
                # AI Pusher is enabled (assumes MQTT method based on current ai_pusher.py)
                if not scheduler.get_job('push_ai_logs'):
                    from .services.ai_pusher import push_logs_to_ai # This function handles MQTT push
                    push_interval = app.config.get('AI_PUSH_INTERVAL_MINUTES', 15)
                    scheduler.add_job(id='push_ai_logs', func=push_logs_to_ai,
                                    trigger='interval', minutes=push_interval)
                    mqtt_host = app.config.get('AI_ENGINE_MQTT_HOST', '?') # Get host for logging
                    logging.warning(f"AI Pusher Enabled: Scheduled log push via MQTT to {mqtt_host} every {push_interval} minutes.") # Keep this one
                else:
                    logging.warning("AI Pusher: Job 'push_ai_logs' already scheduled.") # Keep this one
            else:
                 # logging.warning("DEBUG SCHEDULER: AI_ENABLED is False, printing disabled message.") # Use logging
                 # logging.warning("AI Pusher Disabled (AI_ENGINE_ENABLED is False).") # Keep this one
                 pass # Add pass if the else block becomes empty
        else:
            # logging.warning("DEBUG SCHEDULER: SKIPPED scheduler block because testing_value was True.") # Use logging
            pass # Add pass if the else block becomes empty

        logging.warning(f"App created with config: {config_name}") # Keep this one
        return app
    except Exception as e:
        # --- Log any exception during early init --- #
        logging.error(f"CRITICAL ERROR during create_app early initialization: {e}", exc_info=True) # Keep this one
        import traceback
        # traceback.print_exc() # No need with exc_info=True
        # Optionally re-raise or exit, but printing should show up in logs
        raise # Re-raise to ensure failure is visible