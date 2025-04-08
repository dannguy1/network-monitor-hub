import re
import dateutil.parser
from datetime import datetime, timezone
from .. import db # Need app context for this
from ..models import LogEntry, Device
from flask import current_app

# Regex to parse a common syslog format (RFC 3164 style - adjust if needed)
# Example: <PRI>Timestamp Hostname process[pid]: message
# <30>Oct 11 22:14:15 my-router CRON[12345]: USER root pid 12346 cmd /usr/sbin/ntpclient -i 600 -s -h pool.ntp.org
# We capture priority, timestamp (multiple formats), hostname, process[pid]?, and message
# Note: This regex is a starting point and might need refinement based on actual OpenWRT log formats
SYSLOG_REGEX = re.compile(
    r'^<(?P<pri>\d{1,3})>'
    r'(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[-+]\d{2}:?\d{2})?|\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[-+]\d{2}:?\d{2})?)\s+'
    r'(?P<hostname>[\w\.-]+)\s+'
    r'(?:(?P<process>[\w\/\.-]+)(?:\[(?P<pid>\d+)\])?:\s+)?' # Optional process[pid]:
    r'(?P<message>.*)$'
)

# Mapping syslog priorities to log levels (simplified)
# See RFC 5424 for full severity levels
PRIORITY_LEVELS = {
    0: 'EMERGENCY', 1: 'ALERT', 2: 'CRITICAL', 3: 'ERROR',
    4: 'WARNING', 5: 'NOTICE', 6: 'INFO', 7: 'DEBUG'
}

def parse_syslog_message(raw_message):
    """Parses a raw syslog message string and returns a dictionary or None.
       The dictionary includes the hostname found within the message.
    """
    match = SYSLOG_REGEX.match(raw_message)
    if not match:
        current_app.logger.debug(f"Failed to parse syslog message format: {raw_message[:100]}...")
        # Return minimal info, including raw message for potential later processing
        return {
            "raw_message": raw_message,
            "timestamp": datetime.now(timezone.utc), # Fallback timestamp
            "message": raw_message,
            "log_level": "UNKNOWN",
            "process_name": None,
            "hostname": None, # Cannot determine hostname reliably without parsing
            "structured_data": None,
            "parse_success": False
        }

    data = match.groupdict()

    # Parse timestamp
    try:
        # dateutil.parser handles many formats, but might need hints
        # Assume local time if no timezone specified, then convert to UTC
        ts = dateutil.parser.parse(data['timestamp'])
        if ts.tzinfo is None:
             # VERY IMPORTANT: Assume the source device's timezone if possible,
             # otherwise assume UTC or server local? Assuming UTC if naive.
             # This might need configuration per-device if they aren't set to UTC.
             ts = ts.replace(tzinfo=timezone.utc)
        else:
            ts = ts.astimezone(timezone.utc)
    except ValueError:
        current_app.logger.warning(f"Could not parse timestamp '{data['timestamp']}', using current time.")
        ts = datetime.now(timezone.utc)

    # Determine log level from priority
    try:
        priority = int(data.get('pri', -1))
        severity = priority & 7 # Lower 3 bits are severity
        log_level = PRIORITY_LEVELS.get(severity, "UNKNOWN")
    except (ValueError, TypeError):
        priority = -1 # Ensure priority is defined
        log_level = "UNKNOWN"

    parsed_data = {
        "raw_message": raw_message,
        "timestamp": ts,
        "log_level": log_level,
        "hostname": data.get('hostname'), # Crucial: Keep the hostname from the log
        "process_name": data.get('process'),
        "message": data.get('message', '').strip(),
        "structured_data": { # Basic structured data
            "syslog_priority": priority if priority != -1 else None,
            "syslog_pid": data.get('pid')
        },
        "parse_success": True
    }
    
    # TODO: Add more advanced parsing/structuring here if needed

    return parsed_data

def find_device(identifier):
    """Finds a device by IP address or Name (case-insensitive)."""
    # Try finding by IP first
    device = Device.query.filter(Device.ip_address == identifier).first()
    if device:
        return device, identifier # Return device and the IP used
    # If not found by IP, try by name (case-insensitive)
    device = Device.query.filter(db.func.lower(Device.name) == db.func.lower(identifier)).first()
    if device:
        return device, device.ip_address # Return device and its actual IP
    return None, None # Not found

def process_log_batch(log_batch):
    """Processes a batch of (raw_message, source_identifier) tuples.
       source_identifier can be an IP address (from UDP) or hostname (from file).
    """
    processed_count = 0
    error_count = 0
    logs_to_add = []
    devices_to_update = {} # Track devices whose last_seen needs update {device_id: device_obj}
    received_time = datetime.now(timezone.utc) # Get timestamp for this batch

    # --- Pre-fetch devices based on potential identifiers --- 
    # This is less efficient if identifiers are hostnames, as we might need two queries
    # or fetch all devices. Fetching all might be okay for a small number of devices.
    # For now, we'll look up devices one by one within the loop.
    # Consider optimizing this if performance becomes an issue.

    for raw_message, source_identifier in log_batch:
        parsed_data = parse_syslog_message(raw_message)
        
        # Determine the identifier to use for device lookup
        # If source_identifier is provided (e.g. IP from UDP), use that.
        # Otherwise, use the hostname parsed from the log message (for file processing).
        lookup_identifier = source_identifier if source_identifier else parsed_data.get('hostname')

        if not lookup_identifier:
            current_app.logger.warning(f"Could not determine source identifier for log: {raw_message[:100]}...")
            error_count += 1
            continue
        
        # Find the corresponding device in our database using IP or hostname
        device, device_ip_for_log = find_device(lookup_identifier)

        if not device:
            current_app.logger.warning(f"Received log from unknown device identifier: '{lookup_identifier}'. Log ignored.")
            error_count += 1
            continue

        # Track device for last_seen update (avoid duplicate adds to session)
        if device.id not in devices_to_update:
            devices_to_update[device.id] = device

        # Create LogEntry
        log_entry = LogEntry(
            device_id=device.id,
            # Store the *actual* IP of the found device, not necessarily the lookup_identifier
            device_ip=device_ip_for_log,
            # timestamp=parsed_data['timestamp'], # OLD: Use parsed timestamp
            timestamp=received_time, # NEW: Use arrival timestamp
            log_level=parsed_data.get('log_level'),
            process_name=parsed_data.get('process_name'),
            message=parsed_data['message'],
            raw_message=parsed_data.get('raw_message'),
            structured_data=parsed_data.get('structured_data')
        )
        logs_to_add.append(log_entry)

    # --- Batch Update and Commit --- 
    if logs_to_add:
        try:
            # Update last_seen for all affected devices
            # Use the same received_time for consistency in this batch
            now = received_time 
            for dev in devices_to_update.values():
                 dev.last_seen = now
                 db.session.add(dev) # Add device updates to session
            
            # Add all new log entries
            db.session.add_all(logs_to_add)
            
            db.session.commit()
            processed_count = len(logs_to_add)
            current_app.logger.info(f"Processed and saved {processed_count} log entries. Updated last_seen for {len(devices_to_update)} devices.")
        except Exception as e:
            db.session.rollback()
            error_count += len(logs_to_add) # Count these as errors for this batch run
            current_app.logger.error(f"Failed to save log batch to database: {e}", exc_info=True)
    elif devices_to_update: # Commit if only device updates happened (e.g., processing empty lines)
        try:
            # Use the same received_time for consistency in this batch
            now = received_time
            for dev in devices_to_update.values():
                 dev.last_seen = now
                 db.session.add(dev)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to commit device last_seen updates: {e}", exc_info=True)

    return processed_count, error_count

# Example of how to use this if reading from a file (needs to run in app context):
# def tail_syslog_file(app, file_path):
#     with app.app_context():
#         try:
#             with open(file_path, 'r') as f:
#                 f.seek(0, 2) # Go to end of file
#                 while True:
#                     line = f.readline()
#                     if not line:
#                         time.sleep(0.1)
#                         continue
#                     # Assuming file format doesn't include source IP, need another way?
#                     # Maybe filename pattern or fixed IP per file?
#                     source_ip = "?.?.?.?" # PROBLEM: Need source IP!
#                     process_log_batch([(line.strip(), source_ip)])
#         except FileNotFoundError:
#             current_app.logger.error(f"Syslog file not found: {file_path}")
#         except Exception as e:
#             current_app.logger.error(f"Error reading syslog file: {e}")

# Example using UDP socket server (needs to run in app context):
# import socketserver
# class SyslogUDPHandler(socketserver.BaseRequestHandler):
#     def handle(self):
#         data = self.request[0].strip()
#         socket = self.request[1]
#         source_ip = self.client_address[0]
#         message = data.decode('utf-8', errors='ignore')
#         current_app.logger.debug(f"Received syslog from {source_ip}: {message}")
#         # Process immediately or add to a queue for batching
#         process_log_batch([(message, source_ip)])
#
# def run_syslog_server(app, host="0.0.0.0", port=514):
#     with app.app_context():
#         try:
#             server = socketserver.UDPServer((host, port), SyslogUDPHandler)
#             current_app.logger.info(f"Starting UDP Syslog server on {host}:{port}")
#             server.serve_forever(poll_interval=0.5)
#         except PermissionError:
#              current_app.logger.error(f"Permission denied to bind to port {port}. Try running as root or using a higher port (>1024).")
#         except Exception as e:
#             current_app.logger.error(f"Syslog server error: {e}")
#             server.shutdown() 