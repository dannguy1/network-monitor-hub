from flask import request, jsonify
from . import api
from .. import db
from ..models import LogEntry, Device
from sqlalchemy import desc
import dateutil.parser

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

# Note: POST/PUT/DELETE for individual logs are typically not exposed via API.
# Logs are usually ingested via the syslog mechanism.
# Deletion might happen via background cleanup tasks or specific admin actions if needed. 