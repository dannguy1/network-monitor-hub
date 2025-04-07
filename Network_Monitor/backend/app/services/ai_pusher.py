import requests
import json
from datetime import datetime, timezone
from flask import current_app
from .. import db # Requires app context
from ..models import LogEntry
import time

DEFAULT_BATCH_SIZE = 100
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5 # Simple fixed delay, consider exponential backoff

def push_logs_to_ai(max_batch_size=DEFAULT_BATCH_SIZE):
    """Queries for unprocessed logs and pushes them to the AI engine."""
    ai_endpoint = current_app.config.get('AI_ENGINE_ENDPOINT')
    api_key = current_app.config.get('AI_ENGINE_API_KEY')

    if not ai_endpoint:
        current_app.logger.info("AI_ENGINE_ENDPOINT not configured. Skipping AI push.")
        return 0, 0 # Processed, Failed

    processed_count = 0
    failed_count = 0
    start_time = time.time()

    while True: # Keep processing batches until no more logs or batch limit reached
        logs_to_push = LogEntry.query \
            .filter_by(pushed_to_ai=False) \
            .order_by(LogEntry.timestamp) \
            .limit(max_batch_size) \
            .all()

        if not logs_to_push:
            current_app.logger.debug("No more logs found to push to AI.")
            break # No more logs needing processing

        batch_data = [log.to_dict() for log in logs_to_push] # Use the model's dict representation
        log_ids = [log.id for log in logs_to_push]

        current_app.logger.info(f"Attempting to push batch of {len(batch_data)} logs (IDs: {log_ids[:5]}...) to {ai_endpoint}")

        success = False
        last_error = ""
        for attempt in range(MAX_RETRIES):
            try:
                headers = {'Content-Type': 'application/json'}
                if api_key:
                    headers['Authorization'] = f'Bearer {api_key}' # Or adjust header name as needed
                
                response = requests.post(
                    ai_endpoint,
                    headers=headers,
                    data=json.dumps(batch_data),
                    timeout=15 # Reasonable timeout for API call
                )
                response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                
                # Success!
                current_app.logger.info(f"Successfully pushed batch of {len(log_ids)} logs. Status: {response.status_code}")
                success = True
                processed_count += len(log_ids)
                break # Exit retry loop

            except requests.exceptions.RequestException as e:
                last_error = f"Network/Request error (Attempt {attempt + 1}/{MAX_RETRIES}): {e}"
                current_app.logger.warning(last_error)
            except Exception as e:
                 last_error = f"Unexpected error during push (Attempt {attempt + 1}/{MAX_RETRIES}): {e}"
                 current_app.logger.error(last_error)
            
            # If not successful, wait before retrying
            time.sleep(RETRY_DELAY_SECONDS)

        # --- Update log statuses after processing batch --- 
        if success:
            try:
                # Update pushed status for the successfully processed batch
                LogEntry.query.filter(LogEntry.id.in_(log_ids)) \
                    .update({
                        LogEntry.pushed_to_ai: True,
                        LogEntry.pushed_at: datetime.now(timezone.utc),
                        LogEntry.push_attempts: LogEntry.push_attempts + 1, # Increment attempts anyway
                        LogEntry.last_push_error: None
                    }, synchronize_session=False) # Important for bulk updates
                db.session.commit()
                current_app.logger.debug(f"Updated status for {len(log_ids)} successfully pushed logs.")
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Failed to update status for pushed logs (IDs: {log_ids}): {e}")
                # These logs will be retried later, but AI engine might have them already.
        else:
            # Update failed logs with error and increment attempts
            failed_count += len(log_ids)
            try:
                LogEntry.query.filter(LogEntry.id.in_(log_ids)) \
                    .update({
                        LogEntry.push_attempts: LogEntry.push_attempts + 1,
                        LogEntry.last_push_error: last_error[:1000] # Truncate error if too long
                    }, synchronize_session=False)
                db.session.commit()
                current_app.logger.debug(f"Updated status for {len(log_ids)} failed logs.")
            except Exception as e:
                 db.session.rollback()
                 current_app.logger.error(f"Failed to update status for FAILED logs (IDs: {log_ids}): {e}")
        
        # Optional: Check total processing time and break if it exceeds a limit
        if time.time() - start_time > 60: # Example: Stop after 60 seconds
            current_app.logger.info("AI pusher time limit reached for this run.")
            break

    duration = time.time() - start_time
    current_app.logger.info(f"AI Push run completed in {duration:.2f}s. Processed: {processed_count}, Failed: {failed_count}")
    return processed_count, failed_count

# This function would typically be called by a scheduler (e.g., APScheduler, Celery Beat)
# Example using Flask-APScheduler:
# scheduler = APScheduler()
# @scheduler.task('interval', id='push_ai_logs', minutes=app.config.get('AI_PUSH_INTERVAL_MINUTES', 10))
# def scheduled_ai_push():
#     with app.app_context(): # Need context for db and config
#         push_logs_to_ai() 