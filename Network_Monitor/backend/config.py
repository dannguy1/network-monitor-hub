import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet

# Load environment variables from .env file
basedir = os.path.abspath(os.path.dirname(__file__))
dotenv_path = os.path.join(basedir, '..', '.env') # Point to .env in the Network_Monitor root
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print("Warning: .env file not found. Using default or environment-provided settings.")


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-hard-to-guess-string' # Used for session management, CSRF protection
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY') # MUST be set in .env for credential encryption

    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data', 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # AI Engine Configuration (Placeholders - Set in .env)
    AI_ENGINE_ENDPOINT = os.environ.get('AI_ENGINE_ENDPOINT')
    AI_ENGINE_API_KEY = os.environ.get('AI_ENGINE_API_KEY')
    AI_PUSH_INTERVAL_MINUTES = int(os.environ.get('AI_PUSH_INTERVAL_MINUTES', '10')) # Default 10 mins

    # Syslog configuration (Example: path if reading from file)
    SYSLOG_FILE_PATH = os.environ.get('SYSLOG_FILE_PATH', '/var/log/openwrt-devices.log')

    # Add other configurations as needed
    # e.g., SSH connection timeouts, log rotation settings, etc.

    @staticmethod
    def init_app(app):
        if not Config.ENCRYPTION_KEY:
            raise ValueError("No ENCRYPTION_KEY set for Flask application. Please set it in the .env file.")
        if len(Config.ENCRYPTION_KEY.encode('utf-8')) not in [32, 48, 64]: # Check for AES key sizes (16, 24, 32 bytes -> base64) - Adjust if using raw bytes
             # A more robust check might be needed depending on how the key is generated/encoded.
             # This basic check assumes a base64 encoded key of standard length.
             # For Fernet, it must be a URL-safe base64-encoded 32-byte key.
             pass # Add a check for Fernet key format if using cryptography.fernet

        print(f"Database URI: {Config.SQLALCHEMY_DATABASE_URI}")
        print(f"AI Engine Endpoint: {Config.AI_ENGINE_ENDPOINT}")
        print(f"AI Push Interval: {Config.AI_PUSH_INTERVAL_MINUTES} minutes")
        print(f"Syslog File Path: {Config.SYSLOG_FILE_PATH}")


# You could define different configs for development, testing, production
class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    # Add production specific settings like logging configurations

# Add Testing Config
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'sqlite:///:memory:' # Use in-memory SQLite for tests
    # Disable CSRF protection in forms for testing (if using Flask-WTF later)
    WTF_CSRF_ENABLED = False 
    # Ensure a test encryption key is set if needed, or mock encryption
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY') or Fernet.generate_key().decode() # Generate dummy if not set

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig, # Add testing config
    'default': DevelopmentConfig
} 