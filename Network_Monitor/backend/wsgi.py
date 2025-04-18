# Network_Monitor/backend/wsgi.py
import os
import sys
import traceback
import logging # Import logging

# logging.warning("--- WSGI: Executing wsgi.py ---")

try:
    # logging.warning("--- WSGI: Attempting to import create_app from app ---")
    from app import create_app # Import the factory function
    # logging.warning("--- WSGI: Successfully imported create_app ---")

    # Optionally load .env here if create_app doesn't handle it early enough,
    # but current create_app seems robust.
    # from dotenv import load_dotenv
    # dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    # load_dotenv(dotenv_path)

    # logging.warning("--- WSGI: Attempting to call create_app() ---")
    # Create the Flask app instance using the factory
    # It will automatically use FLASK_CONFIG=production from the environment
    app = create_app()
    # logging.warning("--- WSGI: Successfully called create_app(), app object created ---")

except Exception as e:
    logging.error(f"CRITICAL ERROR in wsgi.py: {e}", exc_info=True) # Log exception info
    # Exit or raise to ensure Gunicorn sees the failure
    sys.exit(1) # Exit with a non-zero code

if __name__ == "__main__":
    # This part is for running directly with `python wsgi.py`, not used by Gunicorn
    # logging.warning("--- WSGI: Running via __main__ (Flask dev server) ---")
    app.run() 