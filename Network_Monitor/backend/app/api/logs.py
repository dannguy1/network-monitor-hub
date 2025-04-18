from flask import request, jsonify, Response, stream_with_context
from flask_login import login_required
from . import api
from .. import db
from ..models import LogEntry, Device
from sqlalchemy import desc
import dateutil.parser
from flask import current_app
import csv
import io
from datetime import datetime

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500

@api.route('/logs', methods=['GET'])
def get_logs():
    """Get a paginated and filterable list of log entries."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', DEFAULT_PAGE_SIZE, type=int)
    per_page = min(per_page, MAX_PAGE_SIZE) # Limit page size

    # --- Filtering --- 
    query = LogEntry.query

    # Filter by Device ID
    device_id = request.args.get('device_id', type=int)
    if device_id:
        query = query.filter(LogEntry.device_id == device_id)

    # Filter by Device IP
    device_ip = request.args.get('device_ip')
    if device_ip:
        # Basic validation, could be more robust
        if len(device_ip) > 45: 
             return jsonify({"error": "Invalid device_ip format"}), 400
        query = query.filter(LogEntry.device_ip.ilike(f'%{device_ip}%'))

    # Filter by Log Level
    log_level = request.args.get('log_level')
    if log_level:
        # Allow case-insensitive matching
        query = query.filter(LogEntry.log_level.ilike(f'%{log_level}%'))

    # Filter by Process Name
    process_name = request.args.get('process_name')
    if process_name:
        query = query.filter(LogEntry.process_name.ilike(f'%{process_name}%'))

    # Filter by Message Content (Keyword Search)
    message_contains = request.args.get('message_contains')
    if message_contains:
        query = query.filter(LogEntry.message.ilike(f'%{message_contains}%'))

    # Filter by Timestamp Range
    start_time_str = request.args.get('start_time')
    end_time_str = request.args.get('end_time')
    try:
        if start_time_str:
            start_time = dateutil.parser.isoparse(start_time_str)
            query = query.filter(LogEntry.timestamp >= start_time)
        if end_time_str:
            end_time = dateutil.parser.isoparse(end_time_str)
            query = query.filter(LogEntry.timestamp <= end_time)
    except ValueError:
        return jsonify({"error": "Invalid timestamp format. Please use ISO 8601 format (e.g., YYYY-MM-DDTHH:MM:SSZ)"}), 400

    # Filter by AI Push Status
    pushed_to_ai = request.args.get('pushed_to_ai')
    if pushed_to_ai is not None:
        if pushed_to_ai.lower() in ['true', '1', 'yes']:
            query = query.filter(LogEntry.pushed_to_ai == True)
        elif pushed_to_ai.lower() in ['false', '0', 'no']:
            query = query.filter(LogEntry.pushed_to_ai == False)

    # --- Sorting --- 
    # Default sort: newest first
    query = query.order_by(desc(LogEntry.timestamp))

    # --- Pagination --- 
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    logs = pagination.items

    # --- Response --- 
    response = {
        'logs': [log.to_dict() for log in logs],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total_pages': pagination.pages,
            'total_items': pagination.total,
            'has_prev': pagination.has_prev,
            'has_next': pagination.has_next,
            'prev_num': pagination.prev_num,
            'next_num': pagination.next_num
        }
    }
    return jsonify(response)

@api.route('/logs/<int:id>', methods=['GET'])
def get_log_entry(id):
    """Get a single log entry by ID."""
    log_entry = db.session.get(LogEntry, id)
    if log_entry is None:
        return jsonify({"error": "Log entry not found"}), 404
    return jsonify(log_entry.to_dict())

@api.route('/logs', methods=['DELETE'])
@login_required
def delete_all_logs():
    """Delete all log entries from the database."""
    try:
        num_deleted = db.session.query(LogEntry).delete()
        db.session.commit()
        current_app.logger.info(f"Deleted {num_deleted} log entries by user request.")
        return jsonify({"message": f"Successfully deleted {num_deleted} log entries."}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting all log entries: {e}", exc_info=True)
        return jsonify({"error": "Failed to delete logs", "message": str(e)}), 500

# Note: POST/PUT/DELETE for individual logs are typically not exposed via API.
# Logs are usually ingested via the syslog mechanism.
# Deletion might happen via background cleanup tasks or specific admin actions if needed.

# --- NEW Export Route --- #
@api.route('/logs/export/<device_identifier>', methods=['GET'])
# @login_required # Consider adding login requirement
def export_logs_csv(device_identifier):
    """Export logs for a specific device to CSV."""
    
    # Find the device by ID, IP, or Name
    device = Device.query.filter(
        (Device.id == device_identifier) | 
        (Device.ip_address == device_identifier) | 
        (Device.name == device_identifier)
    ).first()

    if not device:
        return jsonify({"error": f"Device '{device_identifier}' not found"}), 404

    # Fetch all logs for the device (Consider streaming for large datasets)
    logs = LogEntry.query.filter_by(device_id=device.id).order_by(LogEntry.timestamp.asc()).all()

    if not logs:
        return jsonify({"message": f"No logs found for device '{device_identifier}'"}), 200 # Or 404?

    def generate():
        data = io.StringIO()
        writer = csv.writer(data)

        # Write header row
        writer.writerow([
            'Log ID', 'Timestamp', 'Device IP', 'Device Name', 'Log Level', 
            'Process Name', 'Message', 'Raw Message' # Add more fields if needed
            # 'Structured Data', 'Pushed to AI', 'Pushed At' 
        ])
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)

        # Write data rows
        for log in logs:
            writer.writerow([
                log.id,
                log.timestamp.isoformat() if log.timestamp else '',
                log.device_ip,
                device.name, # Get name from the device object
                log.log_level,
                log.process_name,
                log.message,
                log.raw_message
                # Add other fields corresponding to header
            ])
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)

    # Create filename
    timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename_identifier = device.name.replace(' ', '_') if device.name else device.ip_address
    filename = f"{filename_identifier}_logs_{timestamp_str}.csv"

    # Stream the response
    response = Response(stream_with_context(generate()), mimetype='text/csv')
    response.headers.set("Content-Disposition", "attachment", filename=filename)
    return response
# --- End Export Route --- # 

# --- NEW Raw Export Route --- #
@api.route('/logs/export-raw/<device_identifier>', methods=['GET'])
# @login_required
def export_raw_logs(device_identifier):
    """Export raw log messages for a specific device to a text file."""
    
    device = Device.query.filter(
        (Device.id == device_identifier) | 
        (Device.ip_address == device_identifier) | 
        (Device.name == device_identifier)
    ).first()

    if not device:
        return jsonify({"error": f"Device '{device_identifier}' not found"}), 404

    # Fetch logs efficiently, maybe only necessary columns if needed
    # We need raw_message or fields to reconstruct it
    logs_query = LogEntry.query.filter_by(device_id=device.id).order_by(LogEntry.timestamp.asc())

    # Check if any logs exist before streaming
    if not db.session.query(logs_query.exists()).scalar():
         return jsonify({"message": f"No logs found for device '{device_identifier}'"}), 200

    def generate_raw():
        # Process in chunks to avoid loading all into memory if very large
        chunk_size = 1000 # Adjust as needed
        offset = 0
        while True:
            log_chunk = logs_query.limit(chunk_size).offset(offset).all()
            if not log_chunk:
                break
            
            for log in log_chunk:
                # Use raw_message if available, otherwise construct a basic line
                raw_line = log.raw_message
                if raw_line is None:
                    ts = log.timestamp.strftime('%Y-%m-%d %H:%M:%S') if log.timestamp else ''
                    proc = log.process_name or '-'
                    raw_line = f"{ts} {log.device_ip} {proc}: {log.message}"
                yield raw_line + '\n' # Add newline after each message
            
            offset += chunk_size
            # Add a small delay or check if client disconnected if needed for very long streams

    timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename_identifier = device.name.replace(' ', '_') if device.name else device.ip_address
    filename = f"{filename_identifier}_raw_logs_{timestamp_str}.log"

    response = Response(stream_with_context(generate_raw()), mimetype='text/plain')
    response.headers.set("Content-Disposition", "attachment", filename=filename)
    return response
# --- End Raw Export Route --- # 