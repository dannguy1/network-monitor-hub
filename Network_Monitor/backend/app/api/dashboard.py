from flask import Blueprint, jsonify
from flask_login import login_required
from datetime import datetime, timedelta

# Corrected imports:
from .. import db                 # db is defined in app/__init__.py (one level up)
from ..models import Device, LogEntry # Models are defined in app/models/ (one level up, then down)

# Create Blueprint
bp = Blueprint('dashboard', __name__)

@bp.route('/summary', methods=['GET'])
@login_required
def get_summary():
    """Endpoint to provide summary data for the dashboard."""
    try:
        # Device counts
        total_devices = db.session.query(Device).count()
        managed_devices = db.session.query(Device).filter(Device.credential_id.isnot(None)).count()
        unmanaged_devices = total_devices - managed_devices

        # Log counts (today)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Count logs classified as critical or worse
        critical_levels = ['CRITICAL', 'ALERT', 'EMERGENCY', 'ERROR'] # Include ERROR
        critical_logs_today = db.session.query(LogEntry).filter(
            LogEntry.timestamp >= today_start,
            LogEntry.log_level.in_(critical_levels)
        ).count()

        # Count warning logs
        warning_logs_today = db.session.query(LogEntry).filter(
            LogEntry.timestamp >= today_start,
            LogEntry.log_level == 'WARNING'
        ).count()

        # Placeholder for online/offline status (requires active monitoring implementation)
        # online_devices = ...
        # offline_devices = ...

        summary = {
            'total_devices': total_devices,
            'managed_devices': managed_devices,
            'unmanaged_devices': unmanaged_devices,
            # 'online_devices': online_devices, # Uncomment when implemented
            # 'offline_devices': offline_devices, # Uncomment when implemented
            'critical_logs_today': critical_logs_today,
            'warning_logs_today': warning_logs_today,
        }
        return jsonify(summary), 200

    except Exception as e:
        # Log the exception details here for debugging
        print(f"Error generating dashboard summary: {e}") 
        return jsonify({"error": "Failed to generate dashboard summary"}), 500 