import logging
from flask import Flask, render_template, request, jsonify, Response, flash, redirect, url_for
import threading
import queue
import re # Import re for validation
from typing import Dict, Any, Optional
from ruamel.yaml import YAML # Use ruamel.yaml for safer writing
import os

# --- New Imports for Auth ---
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
# --- Add Flask-WTF imports ---
from flask_wtf.csrf import CSRFProtect # Import CSRFProtect
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
# ---------------------------

logger = logging.getLogger(__name__)

# --- Authentication Setup --- #
login_manager = LoginManager()
csrf = CSRFProtect() # Initialize CSRFProtect

# --- Add LoginForm Definition ---
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')
# ----------------------------

class User(UserMixin):
    """Simple User class for Flask-Login."""
    def __init__(self, id, password_hash=None):
        self.id = id
        self.password_hash = password_hash

    def verify_password(self, password):
        if self.password_hash:
            return check_password_hash(self.password_hash, password)
        return False

# In-memory user storage (replace with DB)
# We only expect one user defined in config
_user_instance: Optional[User] = None

@login_manager.user_loader
def load_user(user_id):
    # Since we only have one user defined in config
    if _user_instance and _user_instance.id == user_id:
        return _user_instance
    return None
# ---------------------------

# Store references passed during app creation
app_context = {}

def create_app(initial_config: Dict[str, Any],
               config_path: str,
               parsed_q: Optional[queue.Queue] = None,
               analysis_q: Optional[queue.Queue] = None,
               analyzer_ref: Optional[Any] = None, # Type depends on AnalyzerManager class
               publisher_ref: Optional[Any] = None, # Type depends on CommandPublisher class
               mqtt_ref: Optional[Any] = None # Type depends on MQTTClient class
               ) -> Flask:
    """Creates and configures the Flask application.

    Args:
        initial_config: The configuration dictionary loaded at startup.
        config_path: The path to the config file (for saving).
        parsed_q: Reference to the parsed log queue.
        analysis_q: Reference to the analysis result queue.
        analyzer_ref: Reference to the AnalyzerManager instance.
        publisher_ref: Reference to the CommandPublisher instance.
        mqtt_ref: Reference to the MQTTClient (ingestion) instance.
    """
    global app_context, _user_instance
    app_context = {
        'config': initial_config,
        'config_path': config_path,
        'parsed_queue': parsed_q,
        'analysis_result_queue': analysis_q,
        'analyzer_manager': analyzer_ref,
        'command_publisher': publisher_ref,
        'mqtt_client': mqtt_ref
    }

    # --- Load User from Config --- #
    ui_config = initial_config.get('web_ui', {})
    username = ui_config.get('username', 'admin')
    password = ui_config.get('password')
    password_hash_config = ui_config.get('password_hash')

    if password and not password_hash_config:
        logger.warning("UI password found in config but no hash. Hashing and recommending update.")
        # Hash the password if it's plain text (for first run/migration)
        password_hash_config = generate_password_hash(password)
        # Ideally, prompt user to update config file with hash and remove plain password
        # For now, we just use the generated hash in memory.

    if password_hash_config:
        _user_instance = User(id=username, password_hash=password_hash_config)
        logger.info(f"Loaded UI user '{username}' with stored password hash.")
    else:
        logger.error("UI password or password_hash not configured. Web UI login will fail.")
        _user_instance = None # Ensure no user if config is bad
    # ---------------------------------

    app = Flask(__name__, template_folder='templates')
    app.config['SECRET_KEY'] = initial_config.get('web_ui', {}).get('secret_key', 'dev-secret-key')
    if not app.config['SECRET_KEY'] or app.config['SECRET_KEY'] == 'dev-secret-key':
        logger.warning("Flask SECRET_KEY is not set or is insecure. Set a strong secret in config.yaml!")

    # --- Initialize Flask-Login --- #
    login_manager.init_app(app)
    login_manager.login_view = 'login' # Route name for the login page
    login_manager.login_message = u"Please log in to access this page."
    login_manager.login_message_category = "info"
    # -------------------------------

    # --- Initialize CSRF Protection --- #
    csrf.init_app(app)
    # --------------------------------

    yaml = YAML()
    yaml.preserve_quotes = True

    # --- Helper to get current status ---
    def get_status_dict() -> Dict[str, Any]:
        return {
            "mqtt_ingestion": "Configured" if app_context['config'].get('message_queue', {}).get('type') == 'mqtt' else "Disabled",
            "parser": "Initialized" if app_context.get('log_parser') else "Not Initialized",
            "analysis_manager": "Running" if app_context.get('analyzer_manager') else "Not Initialized",
            "command_publisher": "Running" if app_context.get('command_publisher') else "Not Initialized",
            "mqtt_connected": app_context['mqtt_client'].client.is_connected() if app_context.get('mqtt_client') else False,
            "parsed_queue_size": app_context['parsed_queue'].qsize() if app_context.get('parsed_queue') else -1,
            "analysis_result_queue_size": app_context['analysis_result_queue'].qsize() if app_context.get('analysis_result_queue') else -1,
            "analyzer_threads": len(app_context['analyzer_manager'].threads) if app_context.get('analyzer_manager') else 0,
        }

    # --- Routes --- #

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        form = LoginForm() # Create form instance
        if form.validate_on_submit(): # Handles POST and validation
            username = form.username.data
            password = form.password.data
            user = load_user(username) # Attempt to load our single user

            if user and user.verify_password(password):
                login_user(user) # Log in the user via Flask-Login
                flash('Logged in successfully.', 'success')
                next_page = request.args.get('next')
                # TODO: Validate next_page URL more robustly
                if next_page and not next_page.startswith('/'): # Basic security check
                    next_page = url_for('index')
                return redirect(next_page or url_for('index'))
            else:
                flash('Invalid username or password', 'danger')
        # For GET request or if validation fails, render template with form
        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('You have been logged out.', 'info')
        return redirect(url_for('login'))

    @app.route('/')
    @login_required # Protect route
    def index():
        return render_template('index.html', status=get_status_dict())

    @app.route('/config', methods=['GET']) # Read-only view
    @login_required # Protect route
    def view_config():
        # Return the *current in-memory* config (doesn't re-read file)
        # Still requires masking
        return jsonify(app_context['config'])

    @app.route('/config/edit', methods=['GET', 'POST'])
    @login_required # Protect route
    def edit_config():
        config_path = app_context['config_path']
        if request.method == 'POST':
            try:
                # Use ruamel.yaml to load existing to preserve structure/comments
                with open(config_path, 'r') as f:
                    current_data = yaml.load(f)

                # --- Update specific sections based on form data ---
                mq_config = current_data.setdefault('message_queue', {})

                # Update MQTT host/port
                if 'mqtt_host' in request.form:
                    mq_config['host'] = request.form['mqtt_host']
                if 'mqtt_port' in request.form:
                    try:
                        mq_config['port'] = int(request.form['mqtt_port'])
                    except (ValueError, TypeError):
                        flash('Invalid MQTT Port number', 'danger')
                        return render_template('edit_config.html', config=current_data)

                # Update MQTT Auth
                if 'mqtt_username' in request.form:
                    mq_config['username'] = request.form['mqtt_username']
                # Only update password if a new one is provided
                if 'mqtt_password' in request.form and request.form['mqtt_password']:
                    mq_config['password'] = request.form['mqtt_password'] # Store plain text - user must secure config file!
                    # Consider hashing or using a secrets management system in a real application.
                    flash('MQTT password updated. Ensure config file permissions are secure.', 'warning')

                # Update MQTT TLS settings
                mq_config['use_tls'] = 'mqtt_use_tls' in request.form
                if 'mqtt_ca_certs' in request.form:
                    mq_config['ca_certs'] = request.form['mqtt_ca_certs']
                if 'mqtt_certfile' in request.form:
                    mq_config['certfile'] = request.form['mqtt_certfile']
                if 'mqtt_keyfile' in request.form:
                    mq_config['keyfile'] = request.form['mqtt_keyfile']

                # Update enabled AI modules (checkboxes)
                ai_config = current_data.setdefault('ai_modules', {})
                if 'ai_modules_enabled[]' in request.form:
                     # Get list of checked modules from form
                     enabled_modules = request.form.getlist('ai_modules_enabled[]')
                     ai_config['enabled'] = enabled_modules
                else: # Handle case where all are unchecked
                     ai_config['enabled'] = []

                # --- Update Parsing Rules --- #
                parsing_config = current_data.setdefault('parsing', {})
                new_rules = []
                rule_index = 0
                has_invalid_regex = False # Flag for validation

                while f'rule_index_{rule_index}' in request.form:
                    index_str = str(rule_index)
                    # Check if delete checkbox is checked for this rule
                    if f'rule_delete_{index_str}' not in request.form:
                        # Not deleted, update it
                        name = request.form.get(f'rule_name_{index_str}', '').strip()
                        pattern = request.form.get(f'rule_pattern_{index_str}', '').strip()
                        if name and pattern:
                            # --- Validate Regex --- #
                            try:
                                re.compile(pattern)
                                new_rules.append({'name': name, 'pattern': pattern})
                            except re.error as e:
                                has_invalid_regex = True
                                flash(f'Rule \'{name}\' has an invalid regex pattern: {e}. Not saved.', 'danger')
                            # ---------------------- #
                        else:
                            # Don't flash warning if just empty, just don't save
                            pass
                    # If deleted, simply don't add it to new_rules
                    rule_index += 1

                # Check for a new rule addition
                new_name = request.form.get('new_rule_name', '').strip()
                new_pattern = request.form.get('new_rule_pattern', '').strip()
                if new_name and new_pattern:
                    # Basic check for duplicate name (can be improved)
                    if any(rule['name'] == new_name for rule in new_rules):
                        flash(f'New rule name "{new_name}" already exists. Not added.', 'warning')
                    else:
                        # --- Validate Regex --- #
                        try:
                            re.compile(new_pattern)
                            new_rules.append({'name': new_name, 'pattern': new_pattern})
                            flash(f'New rule "{new_name}" added.', 'info')
                        except re.error as e:
                            has_invalid_regex = True
                            flash(f'New rule \'{new_name}\' has an invalid regex pattern: {e}. Not added.', 'danger')
                        # ---------------------- #
                elif new_name or new_pattern:
                    # Only warn if one field is filled but not the other
                    flash('New rule was not added because both name and pattern are required.', 'warning')

                # --- Prevent saving if any regex was invalid --- #
                if has_invalid_regex:
                    flash('Errors found in regex patterns. Configuration not saved.', 'danger')
                    # Re-render the form with the submitted (potentially bad) data for correction
                    # This is tricky because we need to reconstruct the `config` object partly
                    # For simplicity now, we reload from file and show errors
                    with open(config_path, 'r') as f:
                        config_data = yaml.load(f)
                    # Pass original rules to template for display
                    return render_template('edit_config.html', config=config_data)
                # -------------------------------------------- #

                parsing_config['rules'] = new_rules
                # ----------------------------

                # TODO: Add more fields as needed (Command Output, etc.)

                # Write back using ruamel.yaml
                with open(config_path, 'w') as f:
                    yaml.dump(current_data, f)

                flash('Configuration updated successfully. Restart service for changes to take effect.', 'success')
                # Update in-memory config for display, but acknowledge restart needed
                app_context['config'] = current_data
                return redirect(url_for('index'))

            except FileNotFoundError:
                flash(f'Error: Config file not found at {config_path}', 'danger')
                return redirect(url_for('index'))
            except Exception as e:
                logger.error(f"Error updating config file {config_path}: {e}", exc_info=True)
                flash(f'Error saving configuration: {e}', 'danger')
                # Try to render form with potentially partially updated data
                return render_template('edit_config.html', config=current_data)

        # GET request: Load current config and render form
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.load(f)
            # Get list of available (discovered) analyzers to populate checkboxes
            available_analyzers = []
            if app_context.get('analyzer_manager'):
                 # Assuming _discover_analyzers is accessible or we get the list differently
                 # This might require refactoring AnalyzerManager slightly
                 # Placeholder:
                 # available_analyzers = list(app_context['analyzer_manager']._discover_analyzers().keys())
                 pass # Need a way to get discovered analyzer names

            return render_template('edit_config.html', config=config_data, available_analyzers=available_analyzers)
        except FileNotFoundError:
             flash(f'Error: Config file not found at {config_path}', 'danger')
             return redirect(url_for('index'))
        except Exception as e:
             logger.error(f"Error loading config file {config_path} for editing: {e}", exc_info=True)
             flash(f'Error loading configuration for edit: {e}', 'danger')
             return redirect(url_for('index'))

    @app.route('/api/status', methods=['GET'])
    @login_required # Protect route
    def api_status():
        return jsonify(get_status_dict())

    logger.info("Flask app created.")
    return app

def run_web_server(config: Dict[str, Any], config_path: str, parsed_q, analysis_q, analyzer_ref, publisher_ref, mqtt_ref):
    """Runs the Flask web server in a separate thread."""
    ui_config = config.get('web_ui', {})
    host = ui_config.get('host', '127.0.0.1')
    port = ui_config.get('port', 8080)
    # debug = ui_config.get('debug', False) # Debug generally off for waitress

    if not ui_config.get('enabled', False):
        logger.info("Web UI is disabled in configuration.")
        return None

    app = create_app(
        config, config_path, parsed_q, analysis_q,
        analyzer_ref, publisher_ref, mqtt_ref
    )

    try:
        from waitress import serve
        thread = threading.Thread(target=serve, args=(app,), kwargs={'host': host, 'port': port}, daemon=True, name="WebServerThread")
        thread.start()
        logger.info(f"Web server started on http://{host}:{port} using waitress.")
        return thread
    except ImportError:
        logger.warning("waitress not installed. Cannot run production web server.")
        return None 