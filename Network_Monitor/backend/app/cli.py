import click
from flask.cli import with_appcontext
import socketserver
import time
import os
import sys

# Import services and models needed for commands
from .services import syslog_processor, ai_pusher
from . import db # If direct db access needed

# Ensure backend is in path for sibling imports if running directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from .models import User, Device
import paho.mqtt.client as paho_mqtt # Import for test command
import ssl # Import for test command
import json # Import for test command

# --- Syslog Listener Command --- 

# Define the handler within the CLI module or import if defined elsewhere
class SyslogUDPHandler(socketserver.BaseRequestHandler):
    # Class needs access to the app context for logging and processing
    # We achieve this by passing the app context into the server or handler if needed,
    # but for direct calls to process_log_batch, we ensure the command runs with app context.
    def handle(self):
        data = self.request[0].strip()
        # socket = self.request[1] # UDP socket
        source_ip = self.client_address[0]
        message = data.decode('utf-8', errors='ignore')
        # IMPORTANT: process_log_batch needs the app context, 
        # which it gets because the entire command runs with_appcontext.
        # Consider batching writes for performance if volume is high.
        syslog_processor.process_log_batch([(message, source_ip)])

@click.command('run-syslog')
@click.option('--host', default='0.0.0.0', help='Host to bind the UDP server to.')
@click.option('--port', default=514, type=int, help='Port to listen for syslog messages on.')
@with_appcontext # Ensures app context is available (for config, logging, db)
def run_syslog_command(host, port):
    """Runs the UDP syslog listener server."""
    from flask import current_app
    
    # --- Determine correct port --- #
    # Prioritize command-line arg if *different* from default.
    # Otherwise, use the config value (from .env).
    config_port_str = current_app.config.get('SYSLOG_UDP_PORT')
    final_port = port # Start with the value from @click.option
    if final_port == 514 and config_port_str: # If cmd line port is default AND config exists
        try:
            final_port = int(config_port_str)
            current_app.logger.info(f"Using SYSLOG_UDP_PORT from config: {final_port}")
        except (ValueError, TypeError):
            current_app.logger.warning(f"Invalid SYSLOG_UDP_PORT ('{config_port_str}') in config, falling back to default/cmd-line: {final_port}")
    # --- End determine port --- #
    
    # Use final_port in logging and binding
    current_app.logger.info(f"Attempting to start UDP Syslog server on {host}:{final_port}")
    
    # Check if port requires root
    if final_port < 1024 and os.geteuid() != 0:
        current_app.logger.warning(f"Port {final_port} is privileged. You might need to run this command with sudo.")

    try:
        # Relying on with_appcontext for process_log_batch
        server = socketserver.UDPServer((host, final_port), SyslogUDPHandler)
        current_app.logger.info(f"UDP Syslog server started successfully on {host}:{final_port}")
        server.serve_forever()
    except PermissionError:
        # Use final_port in error message
        current_app.logger.error(f"Permission denied to bind to port {final_port}. Try running with sudo or using a port > 1024.")
    except OSError as e:
         if "Address already in use" in str(e):
              # Use final_port in error message
              current_app.logger.error(f"Port {final_port} is already in use. Is another service (like rsyslog) listening? ({e})")
         else:
              current_app.logger.error(f"Failed to start syslog server: {e}")
    except Exception as e:
        current_app.logger.error(f"Syslog server crashed: {e}")

# --- Manual Task Triggers --- 

@click.command('trigger-ai-push')
@with_appcontext
def trigger_ai_push_command():
    """Manually triggers the AI log push process (MQTT or HTTP based on config)."""
    # Check config to decide which push function to call
    ai_enabled = current_app.config.get('AI_ENGINE_ENABLED', False)
    ai_method = current_app.config.get('AI_ENGINE_PUSH_METHOD', 'http')

    if not ai_enabled:
        click.echo("AI Pusher is disabled (AI_ENGINE_ENABLED=False). Cannot trigger push.")
        return

    click.echo(f"Triggering AI log push (Method: {ai_method})...")
    try:
        if ai_method == 'mqtt':
            # We call the function directly, it should handle connection/logic
            processed, failed = ai_pusher.push_logs_to_ai()
            click.echo(f"MQTT Push function finished. Attempted: {processed}, Failed Publish: {failed}")
        elif ai_method == 'http':
             # Placeholder for potential future HTTP push function re-implementation
             # processed, failed = ai_pusher.push_logs_to_ai_http() 
             click.echo(f"HTTP Push function (currently placeholder) would run here.")
        else:
             click.echo(f"Unsupported AI push method configured: {ai_method}")

    except Exception as e:
        click.echo(f"Error during manual AI push trigger: {e}")
        import traceback
        traceback.print_exc()

# --- Process Log File Command --- 

# State file to keep track of the last processed position in the log file
STATE_FILE_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

def read_state(state_file):
    """Reads the last processed inode and position."""
    try:
        with open(state_file, 'r') as f:
            line = f.readline().strip()
            if line:
                inode, pos = map(int, line.split(':'))
                return inode, pos
    except (FileNotFoundError, ValueError):
        pass
    return None, 0 # Default if file doesn't exist or is invalid

def write_state(state_file, inode, pos):
    """Writes the current inode and position."""
    try:
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        with open(state_file, 'w') as f:
            f.write(f"{inode}:{pos}")
    except IOError as e:
         # Use Flask logger if available (via app context)
        print(f"Warning: Could not write state file {state_file}: {e}")

@click.command('process-log-file')
@click.argument('filepath', type=click.Path(exists=True, dir_okay=False, readable=True))
@click.option('--batch-size', default=100, help='Number of lines to process per batch.')
@click.option('--state-id', default=None, help='Unique ID for state file (defaults to filename). Used if monitoring multiple files.')
@with_appcontext
def process_log_file_command(filepath, batch_size, state_id):
    """Processes new lines from a log file since the last run.

    Tracks position using a state file in the backend/data directory.
    Handles basic log rotation (inode change).
    """
    from flask import current_app

    state_filename = f".{state_id or os.path.basename(filepath)}.state"
    state_file_path = os.path.join(STATE_FILE_DIR, state_filename)
    current_app.logger.info(f"Starting log processing for '{filepath}'. State file: {state_file_path}")

    processed_total = 0
    errors_total = 0
    start_time = time.time()

    try:
        # Get current file stats and saved state
        file_stat = os.stat(filepath)
        current_inode = file_stat.st_ino
        saved_inode, last_pos = read_state(state_file_path)

        # Check for log rotation
        if saved_inode is not None and saved_inode != current_inode:
            current_app.logger.info(f"Log rotation detected (inode changed from {saved_inode} to {current_inode}). Processing from start of new file.")
            last_pos = 0
        elif saved_inode is None:
             current_app.logger.info("No previous state found. Processing from start of file.")
             last_pos = 0

        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(last_pos)
            batch = []
            while True:
                try:
                    line = f.readline()
                    if not line:
                        # End of file reached for now
                        break 
                    
                    # Pass None as source_identifier, processor will use hostname from log
                    batch.append((line.strip(), None)) 

                    if len(batch) >= batch_size:
                        processed, errors = syslog_processor.process_log_batch(batch)
                        processed_total += processed
                        errors_total += errors
                        batch = [] # Reset batch
                        # Optional: Check elapsed time and yield if it's a long-running task?

                except UnicodeDecodeError as e:
                    current_app.logger.warning(f"Skipping line due to decode error in {filepath} at pos {f.tell()}: {e}")
                    # Attempt to move past the problematic byte/line if possible
                    continue

            # Process any remaining lines in the last batch
            if batch:
                processed, errors = syslog_processor.process_log_batch(batch)
                processed_total += processed
                errors_total += errors

            # Update state with the final position and current inode
            final_pos = f.tell()
            write_state(state_file_path, current_inode, final_pos)
            current_app.logger.debug(f"Updated state: inode={current_inode}, pos={final_pos}")

    except FileNotFoundError:
        current_app.logger.error(f"Log file not found during processing: {filepath}")
        errors_total += 1
    except Exception as e:
        current_app.logger.error(f"Error processing log file '{filepath}': {e}", exc_info=True)
        errors_total += 1 # Count batch processing errors

    duration = time.time() - start_time
    current_app.logger.info(
        f"Finished processing '{filepath}' in {duration:.2f}s. "
        f"Lines Processed (saved to DB): {processed_total}, Errors/Skipped: {errors_total}"
    )

# --- User Management --- 
@click.command('create-user')
@click.argument('username')
@click.password_option()
@with_appcontext
def create_user_command(username, password):
    """Creates a new user."""
    from .models import User
    from . import db
    if User.query.filter_by(username=username).first():
        click.echo(f'Error: User "{username}" already exists.', err=True)
        return
    user = User(username=username, password=password)
    db.session.add(user)
    db.session.commit()
    click.echo(f'User "{username}" created successfully.')

@click.command('seed-admin')
@with_appcontext
def seed_admin_command():
    """Creates the default 'admin' user with password 'admin' if it doesn't exist."""
    from .models import User
    from . import db
    username = 'admin'
    password = 'admin' # Default password
    if User.query.filter_by(username=username).first():
        click.echo(f'User "{username}" already exists. Skipping seed.')
        return
    
    user = User(username=username, password=password)
    db.session.add(user)
    try:
        db.session.commit()
        click.echo(f'Default user "{username}" created successfully.')
    except Exception as e:
        db.session.rollback()
        click.echo(f'Error creating default user "{username}": {e}', err=True)

@click.command('set-password')
@click.argument('username')
@click.password_option(confirmation_prompt=False) # Prompt only once
@with_appcontext
def set_password_command(username, password):
    """Sets or resets the password for an existing user."""
    from .models import User
    from . import db
    user = User.query.filter_by(username=username).first()
    if not user:
        click.echo(f'Error: User "{username}" not found.', err=True)
        return

    # Use the model's password setter to hash the new password
    user.password = password 
    try:
        db.session.commit()
        click.echo(f'Password for user "{username}" updated successfully.')
    except Exception as e:
        db.session.rollback()
        click.echo(f'Error updating password for user "{username}": {e}', err=True)

@click.command('send-test-mqtt')
def send_test_mqtt():
    """Sends a single predefined test message via MQTT to Log-Analyzer."""
    click.echo("Attempting to send test MQTT message...")

    # Check if MQTT push is configured and enabled
    if not current_app.config.get('AI_ENGINE_ENABLED') or current_app.config.get('AI_ENGINE_PUSH_METHOD') != 'mqtt':
        click.echo(click.style("Error: AI Pusher is not enabled or not configured for MQTT in .env", fg='red'))
        return

    host = current_app.config.get('AI_ENGINE_MQTT_HOST')
    port = current_app.config.get('AI_ENGINE_MQTT_PORT')
    topic_prefix = current_app.config.get('AI_ENGINE_MQTT_TOPIC_PREFIX')
    username = current_app.config.get('AI_ENGINE_MQTT_USERNAME')
    password = current_app.config.get('AI_ENGINE_MQTT_PASSWORD')
    use_tls = current_app.config.get('AI_ENGINE_MQTT_TLS_ENABLED')
    ca_certs = current_app.config.get('AI_ENGINE_MQTT_TLS_CA_CERTS')
    qos = 1 # Use standard QoS for testing

    if not host or not port or not topic_prefix:
        click.echo(click.style("Error: Missing MQTT configuration (HOST, PORT, TOPIC_PREFIX) in .env", fg='red'))
        return

    client_id = f"network-monitor-test-sender-{os.getpid()}"
    test_topic = f"{topic_prefix}/test_command"
    test_payload = json.dumps({"test_message": "Hello from Network-Monitor test command!", "timestamp": time.time()})

    click.echo(f"Connecting to {host}:{port}...")
    mqttc = None
    try:
        mqttc = paho_mqtt.Client(client_id=client_id)
        if username:
            mqttc.username_pw_set(username, password)
        if use_tls:
            click.echo("Configuring TLS...")
            mqttc.tls_set(ca_certs=ca_certs, cert_reqs=ssl.CERT_REQUIRED if ca_certs else ssl.CERT_NONE,
                          tls_version=ssl.PROTOCOL_TLSv1_2)
        
        # Synchronous connect for CLI command
        mqttc.connect(host, port, 60)
        mqttc.loop_start() # Start loop for callbacks, though not strictly needed for single publish
        time.sleep(1) # Give a moment to establish connection

        click.echo(f"Publishing to topic '{test_topic}'")
        click.echo(f"Payload: {test_payload}")
        msg_info = mqttc.publish(test_topic, payload=test_payload.encode('utf-8'), qos=qos)
        msg_info.wait_for_publish(timeout=5)

        if msg_info.is_published():
            click.echo(click.style("Test message published successfully!", fg='green'))
        else:
            click.echo(click.style(f"Test message failed to publish (rc={msg_info.rc}). Check broker and Log-Analyzer.", fg='red'))

    except Exception as e:
        click.echo(click.style(f"Error during MQTT test send: {e}", fg='red'))
        import traceback
        traceback.print_exc()
    finally:
        if mqttc:
            click.echo("Disconnecting MQTT client...")
            mqttc.loop_stop()
            mqttc.disconnect()

def register(app):
    """Register CLI commands with the Flask app."""
    app.cli.add_command(run_syslog_command)
    app.cli.add_command(trigger_ai_push_command)
    app.cli.add_command(process_log_file_command)
    app.cli.add_command(create_user_command)
    app.cli.add_command(seed_admin_command)
    app.cli.add_command(set_password_command) # Add the set-password command
    app.cli.add_command(send_test_mqtt) # Add the send-test-mqtt command
    app.logger.info("Registered custom CLI commands.") 