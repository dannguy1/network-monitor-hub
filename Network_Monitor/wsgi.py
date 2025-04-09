import os
import sys
from dotenv import load_dotenv

# Ensure .env is loaded before creating the app, especially for FLASK_CONFIG
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print("Warning: .env file not found in project root for wsgi.")

# Add the backend directory to sys.path if wsgi.py is in the root
# Adjust this based on your actual project structure
project_root = os.path.dirname(__file__) 
backend_path = os.path.join(project_root, 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Use correct import path assuming wsgi.py is in project root
# and app package is inside 'backend'
from backend.app import create_app 

# Determine the config name (e.g., 'development', 'production')
config_name = os.getenv('FLASK_CONFIG', 'production') # Default to production for wsgi
app = create_app(config_name)

if __name__ == "__main__":
    # This is useful for running with `python wsgi.py` for simple testing,
    # but production deployments should use Gunicorn or similar.
    print(f"Running Flask development server (use Gunicorn/Uvicorn for production). Config: {config_name}")
    app.run(debug=app.config.get('DEBUG', False)) 