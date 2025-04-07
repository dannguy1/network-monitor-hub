import os
from dotenv import load_dotenv

# Ensure .env is loaded before creating the app, especially for FLASK_CONFIG
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print("Warning: .env file not found in project root for wsgi.")

from app import create_app # Corrected import path

# Determine the config name (e.g., 'development', 'production')
config_name = os.getenv('FLASK_CONFIG', 'production') # Default to production for wsgi
app = create_app(config_name)

if __name__ == "__main__":
    # This is useful for running with `python wsgi.py` for simple testing,
    # but production deployments should use Gunicorn or similar.
    print(f"Running Flask development server (use Gunicorn/Uvicorn for production). Config: {config_name}")
    app.run(debug=app.config.get('DEBUG', False)) 