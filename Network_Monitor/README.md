# Network Monitor Hub

A full-stack application designed to run efficiently on a Raspberry Pi 5, acting as a central hub for managing and monitoring OpenWRT-based devices. It provides syslog collection, a web UI for log review, credential management, UCI configuration deployment via SSH, and reformatted log data transmission to a remote AI engine.

## Features

*   **Syslog Service:** Collects logs from multiple OpenWRT devices via UDP (default port 514, see `.env.example`).
*   **Web Interface:** A React-based UI featuring:
    *   Dashboard overview.
    *   Device management (Add, Edit, Delete, Credential Association).
    *   Credential management (Add, Edit, Delete - Password/Private Key support).
    *   SSH connection verification.
    *   Remote logging configuration toggle per device.
    *   Log viewing with filtering (by device, level, timestamp, message content) and pagination.
    *   Basic UCI configuration deployment via SSH (Hostname, LAN IP/Netmask/Gateway).
    *   Device reboot command.
*   **UCI Configuration:** Generates and applies UCI commands based on user input through the Web UI.
*   **SSH Deployment:** Applies configurations and commands securely using Paramiko.
*   **Secure Credential Management:** Encrypts stored SSH passwords and private keys using Fernet (`cryptography` library).
*   **Log Processing:** Parses standard syslog messages and stores structured data.
*   **AI Data Transmission:** Periodically pushes structured log data (JSON) to a configurable remote AI engine endpoint via HTTPS (optional feature).
*   **Raspberry Pi 5 Optimized:** Designed with consideration for resource constraints.
*   **Modular Backend:** Uses Flask blueprints and distinct service modules.

## Technology Stack

*   **Backend:** Python 3, Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-APScheduler, Flask-Login, Flask-Limiter, Flask-Cors
*   **Database:** SQLite (default for development), PostgreSQL (recommended for production)
*   **SSH:** Paramiko
*   **Syslog:** Python `socketserver` (UDP listener)
*   **HTTP Requests:** `requests`
*   **Encryption:** `cryptography` (Fernet)
*   **WSGI Server:** Gunicorn (for production)
*   **Frontend:** React, React Router, Axios, Bootstrap, React-Bootstrap, react-bootstrap-icons
*   **Testing:** Pytest (backend), Jest / React Testing Library (frontend)

## Project Structure

```txt
Network_Monitor/
├── backend/
│   ├── app/                # Main Flask application package
│   │   ├── api/            # API Blueprints (auth.py, devices.py, credentials.py, logs.py, uci.py, dashboard.py)
│   │   ├── models/         # SQLAlchemy models (user.py, device.py, credential.py, log_entry.py)
│   │   ├── services/       # Business logic (ssh_manager.py, syslog_processor.py, ai_pusher.py, etc.)
│   │   ├── static/         # (Not currently used by pure API)
│   │   ├── templates/      # (Not currently used by pure API)
│   │   ├── cli.py          # Custom Flask CLI command registration
│   │   └── __init__.py     # Application factory (create_app)
│   ├── data/               # Default location for app.db (SQLite)
│   ├── migrations/         # Flask-Migrate migration scripts
│   ├── tests/              # Backend tests (pytest)
│   ├── venv/               # Python virtual environment (ignored by git)
│   └── config.py           # Configuration classes (DevelopmentConfig, ProductionConfig, TestingConfig)
├── frontend/
│   ├── node_modules/       # Node.js dependencies (ignored by git)
│   ├── public/             # Static assets for React app
│   ├── src/                # React source code
│   │   ├── components/     # React components (Dashboard, DeviceList, LogList, Forms, Modals...)
│   │   ├── context/        # React Context (e.g., AuthContext)
│   │   ├── services/       # API client (api.js)
│   │   ├── App.js          # Main application component with routing
│   │   ├── App.css         # Main styles
│   │   └── index.js        # Entry point for React app
│   ├── .env                # (Optional) Frontend environment variables (e.g., REACT_APP_API_BASE_URL)
│   ├── package.json        # Frontend dependencies and scripts
│   └── ...                 # Other React config/build files (setupTests.js, etc.)
├── .env.example            # Example environment variables for backend
├── .gitignore              # Git ignore rules
├── network-monitor-nginx.conf # Example Nginx configuration for deployment
├── network-monitor-syslog.service # Example systemd service for syslog listener
├── network-monitor-web.service  # Example systemd service for web backend (Gunicorn)
├── requirements.txt        # Backend Python dependencies
└── README.md               # This file
```

## Development Setup

These instructions guide setting up a local development environment.

### Backend

1.  **Prerequisites:** Python 3.8+ installed.
2.  **Clone Repository:**
    ```bash
    git clone <repository_url> Network_Monitor
    cd Network_Monitor
    ```
3.  **Create Python Virtual Environment:**
    ```bash
    python3 -m venv backend/venv
    ```
4.  **Activate Virtual Environment:**
    *   macOS/Linux: `source backend/venv/bin/activate`
    *   Windows (Git Bash/WSL): `source backend/venv/bin/activate`
    *   Windows (CMD): `backend\venv\Scripts\activate`
    *   Windows (PowerShell): `backend\venv\Scripts\Activate.ps1`
    *(Ensure the `(venv)` prefix appears in your terminal prompt.)*
5.  **Install Dependencies:**
    ```bash
    # Ensure virtual environment is active
    pip install -r requirements.txt
    ```
6.  **Configure Environment Variables:**
    *   Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    *   **Edit the `.env` file** (in the `Network_Monitor` root directory):
        *   Generate and set `SECRET_KEY` (e.g., using `openssl rand -hex 32`). **Required.**
        *   Generate and set `ENCRYPTION_KEY` (e.g., using the Python command below). **Required.**
            ```bash
            # Ensure virtualenv is active first!
            python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
            ```
        *   Review `DATABASE_URL`. For development with the default SQLite setup, it's best to **leave this line commented out or remove it entirely**. This allows the application to use the default absolute path configured in `backend/config.py`, which points correctly to `backend/data/app.db`.
        *   If you uncomment `DATABASE_URL` for SQLite, ensure you provide the correct **absolute** path (e.g., `DATABASE_URL=sqlite:////full/path/to/Network_Monitor/backend/data/app.db`). Using a relative path like `sqlite:///data/app.db` will likely cause "unable to open database file" errors when running `flask db` commands.
        *   Configure `AI_ENGINE_*` variables if using the AI push feature.
7.  **Initialize Database & Admin User (First Time Setup):**
    *   Ensure the virtual environment is active (`source backend/venv/bin/activate`).
    *   **Stay in the project root directory (`Network_Monitor`)**.
    *   Set required Flask environment variables:
        ```bash
        # macOS / Linux / Git Bash / WSL:
        export FLASK_APP=backend.app:create_app
        export FLASK_CONFIG=development

        # Windows (CMD):
        # set FLASK_APP=backend.app:create_app
        # set FLASK_CONFIG=development

        # Windows (PowerShell):
        # $env:FLASK_APP="backend.app:create_app"; $env:FLASK_CONFIG="development"
        ```
        *(These tell Flask how to load your app. Run these commands in the same terminal session where you run the `flask db` commands below.)*
    *   Ensure the default data directory exists (for SQLite):
        ```bash
        mkdir -p backend/data
        ```
    *   **Initialize the migration environment** (only run once per project lifetime):
        ```bash
        flask db init
        ```
    *   **Generate the initial migration script** based on your models:
        ```bash
        flask db migrate -m "Initial database schema"
        ```
    *   **Apply the migration** to create/update the database tables:
        ```bash
        flask db upgrade
        ```
    *   **Create your first admin user** (run *after* `flask db upgrade`):
        ```bash
        # Option 1: Automatic default (admin/admin) - MUST CHANGE PASSWORD LATER
        flask seed-admin 
        # Option 2: Manual creation
        # flask create-user <username> # Prompts for password
        ```

8.  **Run Development Web Server:**
    *   Ensure the virtual environment is active.
    *   **Stay in the project root directory (`Network_Monitor`)**.
    *   Ensure `FLASK_APP` and `FLASK_CONFIG` are set (see step 7).
    *   Run the Flask development server:
        ```bash
        flask run --host=0.0.0.0 # Optional: --host=0.0.0.0 to access from other devices
        ```
    *   The backend API should now be running (default: `http://localhost:5000`).
    *   The AI Pusher scheduler (if configured) will start automatically.

### Frontend

1.  **Prerequisites:** Node.js (LTS recommended) and npm installed.
2.  **Navigate to Frontend Directory:**
    ```bash
    cd frontend
    ```
3.  **Install Dependencies:**
    ```bash
    npm install
    ```
4.  **(Optional) Configure Proxy for Separate Backend Host:**
    *   If your backend Flask server is running on a **different host or IP** than your frontend development server (e.g., backend on RPi, frontend on your laptop), you need to configure the React dev server's proxy.
    *   Edit `frontend/package.json` and add a `"proxy"` key pointing to your backend server's base URL:
        ```json
        {
          ...
          "browserslist": {
            ...
          },
          "proxy": "http://<your_backend_ip_or_hostname>:5000" 
        }
        ```
        Replace `<your_backend_ip_or_hostname>` with the actual IP or hostname (e.g., `http://192.168.10.12:5000`).
    *   Ensure you **do not** have `REACT_APP_API_BASE_URL` set in `frontend/.env`, as this would override the proxy.
    *   This proxy allows the browser to make API requests to your frontend server's origin (e.g., `http://localhost:3000/api/v1/...`), which the dev server then forwards to the backend. This avoids cross-origin cookie issues during development.

5.  **Run Development Server:**
    ```bash
    npm start
    ```
    *   The React frontend will open in your browser, usually at `http://localhost:3000`.
    *   If the proxy is configured (Step 4), API requests will be forwarded to the specified backend URL. Otherwise, requests targeting relative paths like `/api/v1` assume the backend runs on the *same* host and port as the frontend dev server (which typically requires Nginx or similar in production but might work if both run on `localhost` in simple dev setups).
    *   The default API base URL in `src/services/api.js` is `/api/v1`. It relies on the proxy (if configured) or expects the backend to be served from the same origin.

## Running Background Tasks (Development)

*   **AI Pusher:** Starts automatically with `flask run` if configured in `.env`.
    *   Manually trigger: `flask trigger-ai-push` (run from project root with venv active and env vars set).
*   **Syslog Listener:**
    *   Needs to run in a **separate terminal** from the main `flask run` process.
    *   Navigate to the project root (`Network_Monitor`).
    *   Ensure the backend virtualenv is active (`source backend/venv/bin/activate`).
    *   Set Flask environment variables (see Backend Step 7).
    *   Run the listener (use a high port like 5140 for dev to avoid needing `sudo`):
        ```bash
        # Example using port 5140
        flask run-syslog --port 5140
        ```
    *   Configure your OpenWRT devices to send syslog messages via UDP to your development machine's IP on the chosen port (e.g., 5140).
    *   **Important:** Make sure no other service (like the system `rsyslog` or another instance of this app) is listening on the same UDP port.

## Testing

### Backend

1.  Ensure virtualenv is active (`source backend/venv/bin/activate`).
2.  Navigate to the project root (`Network_Monitor/`).
3.  Run: `pytest backend/tests/`
    *   Tests use an in-memory SQLite database by default (`TestingConfig`).

### Frontend

1.  Navigate to the frontend directory (`cd frontend`).
2.  Run: `npm test`
    *   Launches the Jest test runner.

## Deployment (Ubuntu / Raspberry Pi Example)

This section provides guidance for deploying the application on an Ubuntu-based system (like Raspberry Pi OS) using the provided automation scripts.

**Assumptions:**
*   Target server has necessary base packages (Python 3, pip, venv, git, Node.js, npm, Nginx, curl, rsync). PostgreSQL is recommended and packages will be installed, but DB/user creation is manual.
*   You are logged in with `sudo` privileges.
*   The server has a static IP or configured DNS.

**1. Prepare Code & Scripts:**
*   Clone the repository to your local machine or directly onto the target server in a temporary location (e.g., your home directory).
    ```bash
    git clone <repository_url> network-monitor-hub
    cd network-monitor-hub
    ```
*   Make the scripts executable:
    ```bash
    chmod +x install_network_monitor.sh update_network_monitor.sh
    ```

**2. Run Installation Script:**
*   Execute the installation script using `sudo`. It will copy the code to `/opt/network-monitor` (by default), set up the environment, build the frontend, and configure systemd/Nginx.
    ```bash
    sudo ./install_network_monitor.sh
    ```

**3. Perform Manual Configuration Steps:**
*   **CRITICAL:** Carefully follow the **MANUAL STEPS REQUIRED** printed at the end of the installation script's output. This includes:
    *   Setting up the PostgreSQL database and user (if using PostgreSQL).
    *   Editing `/opt/network-monitor/.env` to set `DATABASE_URL`, `SECRET_KEY`, `ENCRYPTION_KEY`, etc.
    *   Restarting services (`sudo systemctl restart ...`).
    *   Editing `/etc/nginx/sites-available/network-monitor` to set the correct `server_name`.
    *   Setting up HTTPS (Recommended).
    *   Testing and restarting Nginx (`sudo nginx -t && sudo systemctl restart nginx`).
    *   Configuring the firewall (`ufw` examples provided).
    *   Logging in as the default `admin` user and **changing the password immediately** via the Settings page.
    *   Configuring OpenWRT devices to send logs.

**4. Verify Installation:**
*   Check service status:
    ```bash
    sudo systemctl status network-monitor-web.service network-monitor-syslog.service nginx
    ```
*   Monitor logs:
    ```bash
    sudo journalctl -f -u network-monitor-web -u network-monitor-syslog
    ```
*   Access the web UI in your browser: `http://<YOUR_SERVER_IP_OR_HOSTNAME>`

## Updating the Application

1.  **Update Source Code:**
    *   Navigate to your original project directory (where you have the Git repository).
        ```bash
        cd ~/network-monitor-hub # Or your source location
        ```
    *   Pull the latest changes:
        ```bash
        git pull origin main # Or your branch
        ```
2.  **(Optional) Backup:** Backup `/opt/network-monitor/.env` and your database.
3.  **Run Update Script:**
    *   Execute the update script using `sudo` from your updated source directory.
        ```bash
        sudo ./update_network_monitor.sh
        ```
    *   This script stops services, syncs files using `rsync`, updates dependencies, runs migrations, rebuilds the frontend, resets ownership, and restarts services.
4.  **Verify Update:** Check service status and functionality.

## Configuration Details

*   **Backend:** Configured via `backend/config.py` and environment variables loaded from `.env` (see `.env.example`).
*   **Frontend:** API endpoint configured in `frontend/src/services/api.js`.
*   **Deployment:** Nginx acts as reverse proxy; Gunicorn runs the Flask app; systemd manages services.

## Future Enhancements

*   More sophisticated UI/UX (theming, dashboard improvements, better notifications).
*   Expanded UCI configuration options.
*   REST API controller for devices.
*   Advanced log parsing/analysis.
*   Enhanced background task management (Celery).
*   Comprehensive test coverage.
*   Syslog over TCP/TLS.
*   HTTPS setup via Let's Encrypt/Certbot. 