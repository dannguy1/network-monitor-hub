import paho.mqtt.client as paho_mqtt # Import MQTT client
import json
from datetime import datetime, timezone
from flask import current_app
from .. import db # Requires app context
from ..models import LogEntry
import time
import logging
import ssl

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 100
# MAX_RETRIES = 3 # Less relevant for MQTT fire-and-forget
# RETRY_DELAY_SECONDS = 5

# Global MQTT client instance for this service
mqtt_client: paho_mqtt.Client | None = None
mqtt_connected = False

def _on_connect(client, userdata, flags, rc):
    """Callback for MQTT connection."""
    global mqtt_connected
    if rc == 0:
        logger.info("AI Pusher successfully connected to MQTT broker for log forwarding.")
        mqtt_connected = True
    else:
        logger.error(f"AI Pusher failed to connect to MQTT broker. RC: {rc}")
        mqtt_connected = False

def _on_disconnect(client, userdata, rc):
    """Callback for MQTT disconnection."""
    global mqtt_connected
    logger.warning(f"AI Pusher disconnected from MQTT broker. RC: {rc}")
    mqtt_connected = False
    # Reconnection attempts are handled by loop_start typically

def _ensure_mqtt_connection():
    """Initializes and ensures the MQTT client is connected."""
    global mqtt_client, mqtt_connected

    if not current_app.config.get('LOG_ANALYZER_MQTT_ENABLED'):
        if mqtt_client:
            try:
                mqtt_client.loop_stop()
                mqtt_client.disconnect()
            except Exception as e:
                logger.warning(f"Error stopping existing MQTT client: {e}")
            mqtt_client = None
            mqtt_connected = False
        return False # MQTT is disabled

    if mqtt_client and mqtt_connected:
        return True # Already connected

    if mqtt_client and not mqtt_connected:
        # Attempt reconnect if client exists but isn't connected
        logger.info("Attempting to reconnect AI Pusher MQTT client...")
        try:
            mqtt_client.reconnect()
            # Give some time to reconnect
            time.sleep(2)
            return mqtt_connected
        except Exception as e:
            logger.error(f"Error attempting MQTT reconnect: {e}")
            # Fall through to recreate client

    # Initialize new client
    try:
        host = current_app.config.get('LOG_ANALYZER_MQTT_HOST')
        port = current_app.config.get('LOG_ANALYZER_MQTT_PORT')
        client_id = current_app.config.get('LOG_ANALYZER_MQTT_CLIENT_ID')
        username = current_app.config.get('LOG_ANALYZER_MQTT_USERNAME')
        password = current_app.config.get('LOG_ANALYZER_MQTT_PASSWORD')
        use_tls = current_app.config.get('LOG_ANALYZER_MQTT_USE_TLS')
        ca_certs = current_app.config.get('LOG_ANALYZER_MQTT_TLS_CA_CERTS')

        logger.info(f"Initializing AI Pusher MQTT client for {host}:{port}")
        mqtt_client = paho_mqtt.Client(client_id=client_id)
        mqtt_client.on_connect = _on_connect
        mqtt_client.on_disconnect = _on_disconnect

        if username:
            mqtt_client.username_pw_set(username, password)

        if use_tls:
            logger.info("Configuring TLS for AI Pusher MQTT connection")
            mqtt_client.tls_set(ca_certs=ca_certs, cert_reqs=ssl.CERT_REQUIRED if ca_certs else ssl.CERT_NONE,
                              tls_version=ssl.PROTOCOL_TLSv1_2)

        mqtt_client.connect_async(host, port, 60)
        mqtt_client.loop_start()
        time.sleep(2) # Allow time for connection
        return mqtt_connected

    except Exception as e:
        logger.error(f"Failed to initialize AI Pusher MQTT client: {e}", exc_info=True)
        mqtt_client = None
        mqtt_connected = False
        return False

def push_logs_to_ai(max_batch_size=DEFAULT_BATCH_SIZE):
    """Queries unprocessed logs and pushes them to Log Analyzer via MQTT."""
    global mqtt_client, mqtt_connected

    if not current_app.config.get('LOG_ANALYZER_MQTT_ENABLED'):
        logger.info("LOG_ANALYZER_MQTT_ENABLED is false. Skipping AI push.")
        return 0, 0

    # Ensure MQTT connection is active before processing
    if not _ensure_mqtt_connection():
        logger.warning("Cannot push logs: MQTT client not connected.")
        return 0, 0 # Return 0 processed, 0 failed if no connection

    topic_prefix = current_app.config.get('LOG_ANALYZER_MQTT_TOPIC_PREFIX')
    qos = current_app.config.get('LOG_ANALYZER_MQTT_QOS')

    processed_count = 0
    failed_count = 0
    total_published = 0
    start_time = time.time()

    while True:
        logs_to_push = []
        log_ids = []
        try:
            # Fetch logs needing push
            logs_to_push = LogEntry.query \
                .filter_by(pushed_to_ai=False) \
                .options(db.joinedload(LogEntry.device)) # Eager load device info
                .order_by(LogEntry.timestamp) \
                .limit(max_batch_size) \
                .all()

            if not logs_to_push:
                logger.debug("No more logs found to push to AI.")
                break

            log_ids = [log.id for log in logs_to_push]
            logger.info(f"Processing batch of {len(logs_to_push)} logs for MQTT push (IDs: {log_ids[:5]}...)")

            # Publish each log individually
            batch_processed = 0
            batch_failed = 0
            for log in logs_to_push:
                try:
                    # Determine target topic (e.g., using device hostname or IP as identifier)
                    # Using device.hostname if available, else device_ip
                    device_identifier = log.device.hostname if log.device and log.device.hostname else log.device_ip
                    if not device_identifier:
                         logger.warning(f"Skipping log ID {log.id}: Missing device identifier (hostname/IP).")
                         batch_failed += 1
                         continue

                    target_topic = f"{topic_prefix}/{device_identifier}"
                    # Use raw_message if available, otherwise formatted message
                    payload = log.raw_message if log.raw_message else f"{log.timestamp.strftime('%b %d %H:%M:%S')} {log.device_ip} {log.process_name or '-'}: {log.message}"

                    msg_info = mqtt_client.publish(target_topic, payload=payload.encode('utf-8'), qos=qos)
                    # Optional: Check if publish was queued successfully
                    if msg_info.rc == paho_mqtt.MQTT_ERR_SUCCESS:
                        logger.debug(f"Successfully queued log ID {log.id} to {target_topic}")
                        total_published += 1
                    else:
                        logger.warning(f"Failed to queue log ID {log.id} to {target_topic} (rc={msg_info.rc})")
                        batch_failed += 1

                    batch_processed += 1

                except Exception as pub_err:
                    logger.error(f"Error publishing log ID {log.id}: {pub_err}", exc_info=True)
                    batch_failed += 1

            processed_count += batch_processed
            failed_count += batch_failed

            if log_ids:
                try:
                    LogEntry.query.filter(LogEntry.id.in_(log_ids)) \
                        .update({
                            LogEntry.pushed_to_ai: True,
                            LogEntry.pushed_at: datetime.now(timezone.utc),
                        }, synchronize_session=False)
                    db.session.commit()
                    logger.debug(f"Marked {len(log_ids)} logs as pushed_to_ai=True.")
                except Exception as db_err:
                    db.session.rollback()
                    logger.error(f"Failed to update status for logs (IDs: {log_ids}): {db_err}")

        except Exception as fetch_err:
            logger.error(f"Error fetching logs to push: {fetch_err}", exc_info=True)
            break

        if time.time() - start_time > 60:
            logger.info("AI pusher time limit reached for this run.")
            break

    duration = time.time() - start_time
    logger.info(f"MQTT AI Push run completed in {duration:.2f}s. Attempted: {processed_count}, Failed Publish: {failed_count}, Total Queued: {total_published}")
    return processed_count, failed_count

# This function would typically be called by a scheduler (e.g., APScheduler, Celery Beat)
# Example using Flask-APScheduler:
# scheduler = APScheduler()
# @scheduler.task('interval', id='push_ai_logs', minutes=app.config.get('AI_PUSH_INTERVAL_MINUTES', 10))
# def scheduled_ai_push():
#     with app.app_context(): # Need context for db and config
#         push_logs_to_ai() 