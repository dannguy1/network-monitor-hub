from flask import Blueprint, jsonify, current_app
from flask_login import login_required
from datetime import datetime, timedelta
import socket

# Corrected imports:
from .. import db, scheduler        # Import scheduler instance
from ..models import Device, LogEntry # Models are defined in app/models/ (one level up, then down)

# Create Blueprint
bp = Blueprint('dashboard', __name__)

def is_port_in_use(port, host='0.0.0.0'):
    """Check if a UDP port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            # Try to bind to the port. If it succeeds, the port wasn't in use.
            # If it fails (OSError), the port is likely in use.
            # Use SO_REUSEADDR to allow immediate restart of the listener in some cases,
            # but it might give false negatives if the *exact* same address+port is bound.
            # For checking if *any* process uses the port, this is generally okay.
            s.bind((host, port))
            return False # Bind succeeded, port is free
        except OSError as e:
            # Specific error codes might indicate different things, 
            # but "Address already in use" is the primary indicator.
            current_app.logger.debug(f"Port check for {host}:{port} failed with OSError: {e}")
            return True # Bind failed, port likely in use
        except Exception as e:
             current_app.logger.warning(f"Unexpected error checking port {host}:{port}: {e}")
             return False # Assume not in use on unexpected error

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

        # --- Check Syslog Listener Status --- 
        syslog_port_config = current_app.config.get('SYSLOG_UDP_PORT') # Get configured port
        current_app.logger.debug(f"Dashboard Summary: Read SYSLOG_UDP_PORT from config: '{syslog_port_config}'")
        syslog_status = "Unknown"
        if syslog_port_config:
            try:
                 syslog_port = int(syslog_port_config)
                 # Using 0.0.0.0 as the likely bind address
                 if is_port_in_use(syslog_port, host='0.0.0.0'):
                     syslog_status = "Running"
                 else:
                     syslog_status = "Stopped"
            except ValueError:
                 syslog_status = "Config Error (Invalid Port)"
            except Exception as e:
                current_app.logger.error(f"Error checking syslog port status: {e}")
                syslog_status = "Check Error"
        else:
             syslog_status = "Disabled"

        # --- Check AI Pusher Status --- 
        ai_pusher_status = "Unknown"
        ai_endpoint = current_app.config.get('AI_ENGINE_ENDPOINT')
        if not ai_endpoint:
             ai_pusher_status = "Disabled"
        else:
            try:
                ai_job = scheduler.get_job('push_ai_logs')
                if ai_job:
                     # Check if job is currently running or scheduled
                     # next_run_time gives an indication if it's scheduled
                     if ai_job.next_run_time:
                         ai_pusher_status = "Scheduled"
                     else:
                         # Could be paused or finished? APScheduler states are complex.
                         # Assume "Scheduled" if the job exists and has a next run time.
                         ai_pusher_status = "Inactive (No Next Run)" 
                else:
                     # Job doesn't exist - wasn't scheduled or was removed
                     ai_pusher_status = "Stopped (Not Scheduled)"
            except Exception as e:
                 current_app.logger.error(f"Error checking AI pusher job status: {e}")
                 ai_pusher_status = "Check Error"
        
        summary = {
            'total_devices': total_devices,
            'managed_devices': managed_devices,
            'unmanaged_devices': unmanaged_devices,
            'critical_logs_today': critical_logs_today,
            'warning_logs_today': warning_logs_today,
            'syslog_listener_status': syslog_status,
            'ai_pusher_status': ai_pusher_status,
        }
        return jsonify(summary), 200

    except Exception as e:
        current_app.logger.error(f"Error generating dashboard summary: {e}", exc_info=True)
        return jsonify({"error": "Failed to generate dashboard summary"}), 500 