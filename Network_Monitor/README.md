# Network Monitor Hub

A full-stack application designed to run efficiently on a Raspberry Pi 5, acting as a central hub for managing and monitoring OpenWRT-based devices. It provides syslog collection, a web UI for log review, credential management, UCI configuration deployment via SSH, and reformatted log data transmission to a remote AI engine.

## Features

*   **Syslog Service:** Collects logs from multiple OpenWRT devices via UDP (default port 514).
*   **Web Interface:** A React-based UI for:
    *   Viewing collected logs with filtering (by device, level, timestamp, message content) and pagination.
    *   Managing monitored devices (Add, Edit, Delete).
    *   Managing SSH credentials (Add, Edit, Delete, Password/Private Key support).
    *   Associating/Disassociating credentials with devices.
    *   Verifying SSH connectivity using stored credentials.
    *   Applying basic UCI configurations (Hostname, LAN IP/Netmask/Gateway) via SSH.
*   **UCI Configuration:** Generates and applies UCI commands based on user input through the Web UI.
*   **SSH Deployment:** Applies configurations securely using Paramiko, supporting password and private key authentication.
*   **Secure Credential Management:** Encrypts stored SSH passwords and private keys using Fernet (cryptography library).
*   **Log Reformatting (Basic):** Parses standard syslog messages to extract key fields (timestamp, level, source, process, message) and stores them in a structured format.
*   **AI Data Transmission:** Periodically pushes structured log data (JSON format) to a configurable remote AI engine endpoint via HTTPS. Includes basic retry logic.
*   **Raspberry Pi 5 Optimized:** Designed with consideration for resource constraints.
*   **Modular Backend:** Uses Flask blueprints and distinct service modules.

## Technology Stack

*   **Backend:** Python 3, Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-APScheduler
*   **Database:** SQLite (default), easily configurable for PostgreSQL
*   **SSH:** Paramiko
*   **Syslog:** Python `socketserver` (for UDP listener)
*   **HTTP Requests:** `requests`
*   **Encryption:** `cryptography` (Fernet)
*   **WSGI Server:** Gunicorn (for production)
*   **Frontend:** React, React Router, Axios, Bootstrap, React-Bootstrap
*   **Testing:** Pytest (backend), Jest / React Testing Library (frontend)

## Project Structure

```
Network_Monitor/
├── backend/
│   ├── app/                # Main Flask application package
│   │   ├── api/            # API Blueprints (devices.py, credentials.py, logs.py, uci.py)
│   │   ├── models/         # SQLAlchemy models (device.py, credential.py, log_entry.py)
│   │   ├── services/       # Business logic (ssh_manager.py, syslog_processor.py, ...)
│   │   ├── static/         # (Optional) Static files served by Flask
│   │   ├── templates/      # (Optional) Templates if not using pure SPA frontend
│   │   ├── cli.py          # Custom Flask CLI commands
│   │   └── __init__.py     # Application factory (create_app)
│   ├── data/               # Data files (e.g., app.db - SQLite database)
│   ├── migrations/         # Flask-Migrate migration scripts
│   ├── venv/               # Python virtual environment (ignored by git)
│   └── config.py           # Configuration classes (Dev, Prod, Test)
├── frontend/
│   ├── node_modules/       # Node.js dependencies (ignored by git)
│   ├── public/             # Static assets for React app
│   ├── src/                # React source code
│   │   ├── components/     # React components (DeviceList, LogList, Forms, Modals...)
│   │   ├── services/       # API client (api.js)
│   │   ├── App.js          # Main application component with routing
│   │   ├── App.css         # Main styles
│   │   └── index.js        # Entry point for React app
│   ├── .env                # (Optional) Frontend environment variables
│   ├── package.json        # Frontend dependencies and scripts
│   └── ...                 # Other React config/build files
├── tests/                  # Backend tests (pytest)
│   └── test_basic.py       # Example test file
├── .env.example            # Example environment variables
├── .gitignore              # Git ignore rules
├── network-monitor-nginx.conf # Example Nginx configuration
├── network-monitor-syslog.service # Example systemd service for syslog listener
├── network-monitor-web.service  # Example systemd service for web backend
├── requirements.txt        # Backend Python dependencies
└── README.md               # This file
```

## Development Setup

### Backend

1.  **Prerequisites:** Python 3.8+
2.  **Clone:** `git clone <repository_url> Network_Monitor && cd Network_Monitor`
3.  **Create Virtual Environment:** `python3 -m venv backend/venv`
4.  **Activate Environment:**
    *   macOS/Linux: `source backend/venv/bin/activate`
    *   Windows: `backend\\venv\\Scripts\\activate`
5.  **Install Dependencies:** `pip install -r requirements.txt`
6.  **Environment Variables:**
    *   Copy `.env.example` to `.env` in the project root (`Network_Monitor/.env`).
    *   **Crucially, generate and set `ENCRYPTION_KEY`**:
        *   Run Python: `python`
        *   Enter: `from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())`
        *   Copy the output key into the `ENCRYPTION_KEY` field in `.env`.
    *   Set `SECRET_KEY` to a strong random string.
    *   Configure `DATABASE_URL` if not using the default SQLite path (`backend/data/app.db`).
    *   Configure `AI_ENGINE_ENDPOINT`, `AI_ENGINE_API_KEY`, and `AI_PUSH_INTERVAL_MINUTES` if using the AI push feature.
7.  **Database Initialization:**
    *   Ensure the virtual environment is active (`source backend/venv/bin/activate`).
    *   **Navigate to the `backend` directory:** `cd backend`
    *   Set Flask environment variables **for the `backend` directory**:
        *   macOS/Linux: `export FLASK_APP=app:create_app && export FLASK_CONFIG=development`
        *   Windows (Git Bash/WSL): `export FLASK_APP=app:create_app && export FLASK_CONFIG=development`
        *   Windows (CMD): `set FLASK_APP=app:create_app && set FLASK_CONFIG=development`
        *   Windows (PowerShell): `$env:FLASK_APP="app:create_app"; $env:FLASK_CONFIG="development"`
        *(Note: Using `app:create_app` assumes you are running `flask` commands from within the `backend` directory.)*
    *   Initialize migrations (only once per project): `flask db init`
    *   Create migration script: `flask db migrate -m "Initial models"`
    *   Apply migrations to create database: `flask db upgrade`
    *   **Return to project root:** `cd ..`
8.  **Run Development Server:**
    *   Ensure virtualenv is active (`source backend/venv/bin/activate`).
    *   **Navigate to the `backend` directory:** `cd backend`
    *   Set Flask environment variables (if not already set in your session):
        *   macOS/Linux: `export FLASK_APP=app:create_app && export FLASK_CONFIG=development`
        *   Windows: (Use appropriate command from step 7)
    *   Run: `flask run`
    *   The backend API will be available at `http://localhost:5000`.
    *   The AI Pusher scheduler will start automatically.
    *   **Return to project root:** `cd ..`

### Frontend

1.  **Prerequisites:** Node.js (LTS recommended) and npm.
2.  **Navigate:** `cd frontend` (from the `Network_Monitor` root)
3.  **Install Dependencies:** `npm install`
4.  **Run Development Server:** `npm start`
    *   The frontend will open in your browser, usually at `http://localhost:3000`.
    *   API requests to `/api/v1` will be automatically proxied to the backend server at `http://localhost:5000` (configured in `frontend/package.json`).

## Running Background Tasks (Development)

*   **AI Pusher:** Starts automatically when you run `flask run` due to APScheduler integration. It runs based on the `AI_PUSH_INTERVAL_MINUTES` setting in `.env`. Manually trigger with `flask trigger-ai-push`.
*   **Syslog Listener:**
    *   Needs to run in a separate terminal from `flask run`.
    *   Ensure the backend virtualenv is active (`source backend/venv/bin/activate`).
    *   Run: `flask run-syslog --port 5140` (use a high port like 5140 for dev to avoid needing `sudo`).
    *   Configure your OpenWRT devices to send syslog messages via UDP to your development machine's IP on port 5140.
    *   **Important:** Make sure no other service (like the system `rsyslog`) is listening on the same port you specify.

## Testing

### Backend

1.  Ensure virtualenv is active and test dependencies are installed (`pip install -r requirements.txt`).
2.  Navigate to the project root (`Network_Monitor/`).
3.  Run: `pytest`
    *   Tests use an in-memory SQLite database by default (`TestingConfig`).

### Frontend

1.  Navigate to the frontend directory (`Network_Monitor/frontend/`).
2.  Run: `npm test`
    *   This launches the Jest test runner in watch mode.

## Deployment (Raspberry Pi 5 Example)

These steps provide a guided process for deploying the Network Monitor Hub on a Raspberry Pi OS (or similar Debian-based system). We recommend deploying in `/opt/network-monitor` using a dedicated user.

**Assumptions:**
*   You are logged in as a user with `sudo` privileges (e.g., the default `pi` user).
*   The Raspberry Pi has a static IP address on your network (recommended).
*   Basic familiarity with the Linux command line.

**1. System Preparation & Prerequisites**

*   **Update System:**
    ```bash
    sudo apt update && sudo apt upgrade -y
    ```
*   **Install Required Packages:**
    ```bash
    sudo apt install -y python3 python3-pip python3-venv git nginx curl nodejs npm
    ```
*   **(Optional but Recommended) Create Dedicated User:**
    ```bash
    sudo adduser netmonitor --disabled-password --gecos "" # Create user without password prompt
    sudo usermod -aG sudo netmonitor # Add to sudo group if needed for management
    sudo usermod -aG www-data netmonitor # Add to nginx group for socket access
    sudo mkdir -p /home/netmonitor/.ssh
    sudo cp ~/.ssh/authorized_keys /home/netmonitor/.ssh/ # Copy keys if needed
    sudo chown -R netmonitor:netmonitor /home/netmonitor/.ssh
    # Log in as the new user for subsequent steps (sudo su - netmonitor)
    # Or prefix commands with: sudo -u netmonitor -i -- <<'EOF'
    # YOUR_COMMANDS_HERE
    # EOF
    ```
    *Note: If you use a different user, replace `netmonitor` in subsequent commands and service file configurations.* 

**2. Clone Application Code**

*   **Clone the Repository:** (Run as the `netmonitor` user or adjust ownership later)
    ```bash
    git clone <repository_url> /opt/network-monitor 
    # If cloned as sudo/root, change ownership:
    # sudo chown -R netmonitor:netmonitor /opt/network-monitor
    cd /opt/network-monitor
    ```

**3. Backend Setup**

*   **Create Python Virtual Environment:**
    ```bash
    # Ensure you are in /opt/network-monitor
    # Run as netmonitor user if possible:
    # sudo -u netmonitor -i python3 -m venv backend/venv
    python3 -m venv backend/venv 
    ```
*   **Activate Virtual Environment:**
    ```bash
    source backend/venv/bin/activate
    ```
*   **Install Python Dependencies:**
    ```bash
    # Ensure venv active
    pip install -r requirements.txt
    pip install gunicorn # Install Gunicorn for production server
    ```
*   **Configure Environment (`.env` file):**
    *   Copy the example: `cp .env.example .env`
    *   **Generate Encryption Key:** Run this command and copy the output:
        ```bash
        # Ensure venv active
        python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
        ```
    *   **Edit `.env` file:** `nano .env`
        *   Paste the generated key into `ENCRYPTION_KEY=`. **KEEP THIS KEY SAFE!**
        *   Set `SECRET_KEY=` to a long, random string (e.g., use `openssl rand -hex 32` to generate one).
        *   Set `FLASK_CONFIG=production`.
        *   Review `DATABASE_URL` (default SQLite is `sqlite:////opt/network-monitor/backend/data/app.db`).
        *   Configure `AI_ENGINE_ENDPOINT`, `AI_ENGINE_API_KEY`, `AI_PUSH_INTERVAL_MINUTES` if using the AI push feature.
    *   **Set Permissions for `.env`:**
        ```bash
        # Ensure ownership is correct (e.g., netmonitor:netmonitor if using that user)
        # sudo chown netmonitor:netmonitor .env 
        chmod 600 .env 
        ```
*   **Initialize/Upgrade Database:**
    ```bash
    # Ensure venv is active: source backend/venv/bin/activate
    flask db upgrade # Creates DB and applies migrations
    ```
*   **Create Data Directory (if needed) and Set Permissions:**
    ```bash
    mkdir -p backend/data
    # Ensure the user running the services (netmonitor) can write here
    # sudo chown -R netmonitor:netmonitor backend/data 
    # (If running as netmonitor, permissions should be okay)
    ```
*   **Deactivate venv for now:** `deactivate`

**4. Frontend Build**

*   **Navigate to Frontend Directory:**
    ```bash
    cd frontend
    ```
*   **Install Dependencies:**
    ```bash
    npm install
    ```
*   **Build Static Files:**
    ```bash
    npm run build # Output goes to frontend/build/
    ```
*   **Return to Project Root:**
    ```bash
    cd ..
    ```

**5. Configure System Services (systemd)**

*This setup uses the application's built-in syslog listener.* 

*   **(Important) Disable System Syslog Listener (if running):** We need port 514 for the app.
    ```bash
    sudo systemctl stop rsyslog # Or syslog-ng
    sudo systemctl disable rsyslog # Or syslog-ng
    ```
*   **Prepare Service Files:**
    *   Review the example service files (`network-monitor-web.service`, `network-monitor-syslog.service`).
    *   **Crucially, ensure paths and user/group match your setup.** 
        *   Edit the files (`nano network-monitor-web.service`, etc.).
        *   Verify `User=netmonitor`, `Group=netmonitor` (or your chosen user/group).
        *   Verify `WorkingDirectory=/opt/network-monitor`.
        *   Verify paths to `gunicorn`, `flask` (e.g., `/opt/network-monitor/backend/venv/bin/gunicorn`).
        *   Verify the socket path (`/tmp/network-monitor.sock`) matches the Nginx config.
*   **Copy Service Files:**
    ```bash
    sudo cp network-monitor-web.service /etc/systemd/system/
    sudo cp network-monitor-syslog.service /etc/systemd/system/
    ```
*   **Reload systemd, Enable & Start Services:**
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable network-monitor-web.service
    sudo systemctl enable network-monitor-syslog.service
    sudo systemctl start network-monitor-web.service
    sudo systemctl start network-monitor-syslog.service
    ```
*   **Check Service Status:**
    ```bash
    sudo systemctl status network-monitor-web.service
    sudo systemctl status network-monitor-syslog.service
    # View logs if needed:
    # sudo journalctl -u network-monitor-web.service -f
    # sudo journalctl -u network-monitor-syslog.service -f 
    ```

**6. Configure Web Server (Nginx)**

*   **Prepare Nginx Configuration:**
    *   Edit the example file: `nano network-monitor-nginx.conf`
    *   Replace `YOUR_SERVER_IP_OR_HOSTNAME` with your Pi's actual IP address or DNS name.
    *   Verify `root /opt/network-monitor/frontend/build;` points to the correct build output.
    *   Verify `proxy_pass unix:/tmp/network-monitor.sock;` matches the socket path in `network-monitor-web.service`.
*   **Copy & Enable Nginx Site:**
    ```bash
    sudo cp network-monitor-nginx.conf /etc/nginx/sites-available/network-monitor
    sudo ln -s /etc/nginx/sites-available/network-monitor /etc/nginx/sites-enabled/
    # Remove default site if it exists to avoid conflicts
    sudo rm -f /etc/nginx/sites-enabled/default 
    ```
*   **Test and Restart Nginx:**
    ```bash
    sudo nginx -t # Test configuration
    sudo systemctl restart nginx
    ```

**7. Final Steps & Verification**

*   **Configure OpenWRT Devices:** Point your OpenWRT devices' remote syslog settings to your Raspberry Pi's IP address, using UDP port 514.
*   **Access Web UI:** Open a web browser and navigate to `http://<YOUR_SERVER_IP_OR_HOSTNAME>`.
*   **Create Admin User:** Access the server and run (ensure venv is active):
    ```bash
    cd /opt/network-monitor
    source backend/venv/bin/activate
    # You might need to run flask db upgrade again here if it failed earlier due to permissions
    # flask db upgrade 
    flask create-user <username> <password>
    deactivate
    ```
*   **Log In:** Use the credentials created above to log into the web UI.
*   **Test Functionality:**
    *   Check if logs from your OpenWRT devices appear in the UI.
    *   Add devices and credentials.
    *   Test credential association and verification.
    *   Test log configuration toggle.
    *   Test applying UCI commands via the modal (`/apply_config` endpoint).
    *   Test device reboot.
    *   Test device status refresh.
*   **Monitor Logs:** Keep an eye on systemd service logs (`journalctl`) for any errors during operation.

## Configuration Details

*   **Backend:** Main configuration is handled by `backend/config.py`, reading from `/opt/network-monitor/.env`. Key settings include `DATABASE_URL`, `SECRET_KEY`, `ENCRYPTION_KEY`.
*   **Device Control:** Devices have a `control_method` attribute (default: `ssh`). Backend uses a controller pattern (`services/controllers.py`) to abstract interaction (currently `SSHDeviceController`).
*   **Frontend:** API requests are proxied by Nginx to the backend Gunicorn server via a Unix socket (`/tmp/network-monitor.sock`).
*   **Services:** Managed by `systemd` using the provided `.service` files. Logs viewable via `journalctl`.

## Updating the Application

1.  Navigate to the application directory: `cd /opt/network-monitor`
2.  Stop the services: `sudo systemctl stop network-monitor-web.service network-monitor-syslog.service`
3.  Pull the latest code: `git pull origin main` (or your branch)
4.  Update backend dependencies (if `requirements.txt` changed):
    ```bash
    source backend/venv/bin/activate
    pip install -r requirements.txt
    # Apply any new database migrations
    flask db upgrade 
    deactivate
    ```
5.  Rebuild frontend (if frontend code changed):
    ```bash
    cd frontend
    npm install # If package.json changed
    npm run build
    cd ..
    ```
6.  Copy updated service or Nginx files if they changed:
    ```bash
    # Example: sudo cp network-monitor-web.service /etc/systemd/system/
    # Example: sudo cp network-monitor-nginx.conf /etc/nginx/sites-available/network-monitor
    ```
7.  Reload daemons and restart services:
    ```bash
    sudo systemctl daemon-reload # If service files changed
    # sudo nginx -t && sudo systemctl restart nginx # If nginx config changed
    sudo systemctl start network-monitor-web.service network-monitor-syslog.service
    ```

## Future Enhancements

*   More sophisticated UI/UX (theming, dashboard, detailed views, better notifications).
*   Expanded UCI configuration options in the UI (e.g., WiFi, firewall rules).
*   User interface for selecting device `control_method` (SSH/REST).
*   Implementation of `RESTDeviceController`.
*   Advanced log parsing (e.g., key-value extraction from messages).
*   More robust error handling and reporting.
*   Enhanced background task management (e.g., using Celery).
*   Comprehensive backend and frontend test coverage.
*   Option to configure syslog listener port/protocol (TCP).
*   HTTPS setup for Nginx (using Let's Encrypt or self-signed certs). 