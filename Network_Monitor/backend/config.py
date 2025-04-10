import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet

# Load environment variables from .env file
basedir = os.path.abspath(os.path.dirname(__file__))
# REMOVE initial dotenv loading - let create_app handle it reliably.
# dotenv_path = os.path.join(basedir, '..', '.env') 
# if os.path.exists(dotenv_path):
#     load_dotenv(dotenv_path)
# else:
#     print("Warning: .env file not found. Using default or environment-provided settings.")


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
    AI_PUSH_INTERVAL_MINUTES = int(os.environ.get('AI_PUSH_INTERVAL_MINUTES', '15')) # Default 15 mins

    # --- AI Pusher Method & MQTT Config (Additions) --- #
    AI_ENGINE_ENABLED = os.environ.get('AI_ENGINE_ENABLED', 'false') # Load as string
    AI_ENGINE_PUSH_METHOD = os.environ.get('AI_ENGINE_PUSH_METHOD', 'http') # http, mqtt
    AI_ENGINE_MQTT_HOST = os.environ.get('AI_ENGINE_MQTT_HOST', 'localhost')
    AI_ENGINE_MQTT_PORT = int(os.environ.get('AI_ENGINE_MQTT_PORT', '1883'))
    AI_ENGINE_MQTT_TOPIC_PREFIX = os.environ.get('AI_ENGINE_MQTT_TOPIC_PREFIX', 'network_monitor/logs')
    AI_ENGINE_MQTT_USERNAME = os.environ.get('AI_ENGINE_MQTT_USERNAME')
    AI_ENGINE_MQTT_PASSWORD = os.environ.get('AI_ENGINE_MQTT_PASSWORD')
    AI_ENGINE_MQTT_TLS_ENABLED = os.environ.get('AI_ENGINE_MQTT_TLS_ENABLED', 'false') # Load as string
    AI_ENGINE_MQTT_TLS_CA_CERTS = os.environ.get('AI_ENGINE_MQTT_TLS_CA_CERTS')

    # Syslog Server (Built-in) Configuration
    SYSLOG_UDP_PORT = os.environ.get('SYSLOG_UDP_PORT')
    # SYSLOG_FILE_PATH = os.environ.get('SYSLOG_FILE_PATH', '/var/log/openwrt-devices.log') # Keep if needed for file processing

    # --- Log Analyzer Integration (MQTT) --- #
    LOG_ANALYZER_MQTT_ENABLED = os.environ.get('LOG_ANALYZER_MQTT_ENABLED', 'false').lower() == 'true'
    LOG_ANALYZER_MQTT_HOST = os.environ.get('LOG_ANALYZER_MQTT_HOST', 'localhost')
    LOG_ANALYZER_MQTT_PORT = int(os.environ.get('LOG_ANALYZER_MQTT_PORT', '1883'))
    # Base topic prefix where Log Analyzer ingests logs (e.g., network_monitor/logs)
    LOG_ANALYZER_MQTT_TOPIC_PREFIX = os.environ.get('LOG_ANALYZER_MQTT_TOPIC_PREFIX', 'network_monitor/logs')
    LOG_ANALYZER_MQTT_USERNAME = os.environ.get('LOG_ANALYZER_MQTT_USERNAME') # Optional
    LOG_ANALYZER_MQTT_PASSWORD = os.environ.get('LOG_ANALYZER_MQTT_PASSWORD') # Optional
    LOG_ANALYZER_MQTT_USE_TLS = os.environ.get('LOG_ANALYZER_MQTT_USE_TLS', 'false').lower() == 'true'
    LOG_ANALYZER_MQTT_TLS_CA_CERTS = os.environ.get('LOG_ANALYZER_MQTT_TLS_CA_CERTS') # Path to CA certs if needed
    LOG_ANALYZER_MQTT_QOS = int(os.environ.get('LOG_ANALYZER_MQTT_QOS', '1'))
    LOG_ANALYZER_MQTT_CLIENT_ID = os.environ.get('LOG_ANALYZER_MQTT_CLIENT_ID', 'network_monitor_pusher')

    # Add other configurations as needed
    SSH_TIMEOUT = int(os.environ.get('SSH_TIMEOUT', '10'))
    FRONTEND_ORIGIN = os.environ.get('FRONTEND_ORIGIN', 'http://localhost:3000')

    @staticmethod
    def init_app(app):
        if not Config.ENCRYPTION_KEY:
            raise ValueError("No ENCRYPTION_KEY set for Flask application. Please set it in the .env file.")
        if len(Config.ENCRYPTION_KEY.encode('utf-8')) not in [32, 48, 64]: # Check for AES key sizes (16, 24, 32 bytes -> base64) - Adjust if using raw bytes
             # A more robust check might be needed depending on how the key is generated/encoded.
             # This basic check assumes a base64 encoded key of standard length.
             # For Fernet, it must be a URL-safe base64-encoded 32-byte key.
             pass # Add a check for Fernet key format if using cryptography.fernet

        print(f"Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
        print(f"AI Engine Endpoint: {app.config.get('AI_ENGINE_ENDPOINT')}")
        print(f"AI Push Interval: {app.config.get('AI_PUSH_INTERVAL_MINUTES')} minutes")
        print(f"Syslog UDP Port: {app.config.get('SYSLOG_UDP_PORT')}")
        print(f"SSH Timeout: {app.config.get('SSH_TIMEOUT')}")
        print(f"Frontend Origin: {app.config.get('FRONTEND_ORIGIN')}")


# You could define different configs for development, testing, production
class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False # Explicitly set TESTING to False for production
    # Add production specific settings like logging configurations
    # For example, configuring logging to a file:
    # import logging
    # from logging.handlers import RotatingFileHandler
    # LOG_FILE = os.environ.get('PROD_LOG_FILE') or '/var/log/network-monitor/app.log'
    # LOG_LEVEL = logging.INFO

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