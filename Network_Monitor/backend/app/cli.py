import click
from flask.cli import with_appcontext
import socketserver
import time
import os

# Import services and models needed for commands
from .services import syslog_processor, ai_pusher
from . import db # If direct db access needed

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
    current_app.logger.info(f"Attempting to start UDP Syslog server on {host}:{port}")
    
    # Check if port requires root
    if port < 1024 and os.geteuid() != 0:
        current_app.logger.warning(f"Port {port} is privileged. You might need to run this command with sudo.")

    try:
        # Pass app context or necessary config/db session to Handler if needed
        # For now, relying on with_appcontext for process_log_batch
        server = socketserver.UDPServer((host, port), SyslogUDPHandler)
        current_app.logger.info(f"UDP Syslog server started successfully on {host}:{port}")
        server.serve_forever()
    except PermissionError:
        current_app.logger.error(f"Permission denied to bind to port {port}. Try running with sudo or using a port > 1024.")
    except OSError as e:
         if "Address already in use" in str(e):
              current_app.logger.error(f"Port {port} is already in use. Is another service (like rsyslog) listening? ({e})")
         else:
              current_app.logger.error(f"Failed to start syslog server: {e}")
    except Exception as e:
        current_app.logger.error(f"Syslog server crashed: {e}")
        # Optional: server.shutdown() if needed, but serve_forever usually handles cleanup

# --- Manual Task Triggers --- 

@click.command('trigger-ai-push')
@with_appcontext
def trigger_ai_push_command():
    """Manually triggers the AI log push process."""
    from flask import current_app
    current_app.logger.info("Manually triggering AI log push...")
    processed, failed = ai_pusher.push_logs_to_ai()
    current_app.logger.info(f"Manual AI log push complete. Processed: {processed}, Failed: {failed}")

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

def register(app):
    """Register CLI commands with the Flask app."""
    app.cli.add_command(run_syslog_command)
    app.cli.add_command(trigger_ai_push_command)
    app.cli.add_command(process_log_file_command)
    app.cli.add_command(create_user_command)
    app.cli.add_command(seed_admin_command)
    app.cli.add_command(set_password_command) # Add the set-password command
    app.logger.info("Registered custom CLI commands.") 