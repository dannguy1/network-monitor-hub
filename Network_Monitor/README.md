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
7.  **Initialize Database (First Time Setup):**
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
    *   **Generate the initial migration script** based on your models (run this after `init` or whenever models change):
        ```bash
        flask db migrate -m "Initial database schema" 
        # Use a descriptive message if migrating model changes later
        ```
    *   **Apply the migration** to create/update the database tables (run this after `migrate`):
        ```bash
        flask db upgrade
        ```
    *   **Create your first admin user** (run *after* `flask db upgrade`):
        ```bash
        flask create-user <username> 
        # You will be prompted securely for the password
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

## Deployment (Raspberry Pi 5 Example)

These steps provide a general guide for deploying on a Debian-based system like Raspberry Pi OS. Adapt paths and user names as needed. Deploying under a dedicated user (e.g., `netmonitor`) in `/opt/network-monitor` is recommended.

**Assumptions:**
*   Target server has necessary base packages (Python 3, pip, venv, git, Node.js, npm, Nginx).
*   You are logged in with `sudo` privileges.
*   The server has a static IP or configured DNS.

**1. System Preparation**

*   **Update System & Install Packages:**
    ```bash
    sudo apt update && sudo apt upgrade -y
    sudo apt install -y python3 python3-pip python3-venv git nginx curl nodejs npm
    ```
*   **(Recommended) Create Dedicated User (`netmonitor`):**
    ```bash
    sudo adduser netmonitor --disabled-password --gecos ""
    sudo usermod -aG www-data netmonitor # For Nginx socket access
    # Optional: Add to sudo if needed for management tasks
    # sudo usermod -aG sudo netmonitor
    # Optional: Copy SSH keys if needed for direct login
    # sudo mkdir -p /home/netmonitor/.ssh
    # sudo cp ~/.ssh/authorized_keys /home/netmonitor/.ssh/
    # sudo chown -R netmonitor:netmonitor /home/netmonitor/.ssh
    ```
    *(Adjust user/group in subsequent steps and service files if not using `netmonitor`.)*

**2. Deploy Application Code**

*   **Create Directory & Clone:**
    ```bash
    sudo mkdir -p /opt/network-monitor
    sudo chown netmonitor:netmonitor /opt/network-monitor # Assign ownership
    sudo -u netmonitor git clone <repository_url> /opt/network-monitor
    cd /opt/network-monitor
    ```

**3. Backend Setup**

*   **Create Virtual Environment:**
    ```bash
    sudo -u netmonitor python3 -m venv backend/venv
    ```
*   **Activate Virtual Environment:**
    ```bash
    source backend/venv/bin/activate
    ```
*   **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    pip install gunicorn # Production WSGI server
    ```
*   **Configure Environment (`.env` file):**
    *   `sudo -u netmonitor cp .env.example .env`
    *   **Edit `.env` as the `netmonitor` user:** `sudo -u netmonitor nano .env`
        *   Set `FLASK_CONFIG=production`.
        *   Set a strong `SECRET_KEY`.
        *   Generate and set a unique `ENCRYPTION_KEY` (see Dev Setup Step 6) - **Backup this key!**
        *   Set `DATABASE_URL` (Strongly recommend PostgreSQL for production).
        *   Configure `FRONTEND_ORIGIN` if your frontend is served from a different domain/port than the backend API.
        *   Configure `AI_ENGINE_*` variables if used.
        *   Review `SYSLOG_UDP_PORT` (default 514).
    *   **Set Permissions:** `sudo -u netmonitor chmod 600 .env`
*   **Apply Database Migrations:**
    ```bash
    # Ensure venv active
    # Set ENV variables for flask command
    export FLASK_APP=backend.app:create_app
    export FLASK_CONFIG=production
    flask db upgrade # Apply migrations
    unset FLASK_APP FLASK_CONFIG # Unset temporary variables
    ```
*   **Create Data Directory (if using SQLite - not recommended for prod):**
    ```bash
    # sudo -u netmonitor mkdir -p backend/data
    ```
*   **Deactivate venv for now:** `deactivate`

**4. Frontend Build**

*   **Navigate & Install Dependencies:**
    ```bash
    cd frontend
    # Run npm install as the user who owns the directory if possible
    # If sudo is needed, ensure permissions are fixed later if necessary
    npm install
    ```
*   **Build Static Files:**
    ```bash
    npm run build # Output goes to frontend/build/
    ```
*   **Return to Project Root:** `cd ..`
*   **(Optional) Fix Permissions:** If `npm install/build` created files as root, ensure the `netmonitor` user or `www-data` group can access the `frontend/build` directory as needed by Nginx.
    ```bash
    # Example: sudo chown -R netmonitor:netmonitor frontend/
    ```

**5. Configure System Services (systemd)**

*   **(Important) Disable System Syslog:** If using the app's listener on port 514.
    ```bash
    sudo systemctl stop rsyslog && sudo systemctl disable rsyslog
    ```
*   **Prepare Service Files:**
    *   Review `network-monitor-web.service` and `network-monitor-syslog.service`.
    *   **Verify paths:** `WorkingDirectory`, `ExecStart` (path to `gunicorn`/`flask` in venv).
    *   **Verify:** `User=netmonitor`, `Group=netmonitor` (or your chosen user/group).
    *   Ensure the `.sock` path matches the Nginx config.
    *   Make sure the `Environment` lines correctly point to your `.env` file and set `FLASK_CONFIG=production`.
*   **Copy, Enable & Start Services:**
    ```bash
    sudo cp network-monitor-web.service /etc/systemd/system/
    sudo cp network-monitor-syslog.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable --now network-monitor-web.service # Enable and start
    sudo systemctl enable --now network-monitor-syslog.service # Enable and start
    ```
*   **Check Status:**
    ```bash
    sudo systemctl status network-monitor-web.service network-monitor-syslog.service
    # View logs: sudo journalctl -u network-monitor-web -f
    ```

**6. Configure Web Server (Nginx)**

*   **Prepare Nginx Configuration (`network-monitor-nginx.conf`):**
    *   Replace `YOUR_SERVER_IP_OR_HOSTNAME` with your server's actual IP/DNS name.
    *   Verify `root /opt/network-monitor/frontend/build;` is correct.
    *   Verify `proxy_pass unix:/tmp/network-monitor.sock;` matches the systemd service.
    *   **(Recommended)** Add configuration for HTTPS (e.g., using Let's Encrypt).
*   **Copy & Enable Nginx Site:**
    ```bash
    sudo cp network-monitor-nginx.conf /etc/nginx/sites-available/network-monitor
    sudo ln -s /etc/nginx/sites-available/network-monitor /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default # Avoid conflicts
    ```
*   **Test and Restart Nginx:**
    ```bash
    sudo nginx -t
    sudo systemctl restart nginx
    ```

**7. Final Steps & Verification**

*   **Configure Firewall:** Ensure ports (e.g., 80/443 for HTTP/S, 514/UDP for syslog) are open.
*   **Configure OpenWRT Devices:** Point remote syslog to your server's IP, using the configured UDP port (e.g., 514).
*   **Access Web UI:** `http(s)://<YOUR_SERVER_IP_OR_HOSTNAME>`.
*   **Create Admin User (if not done during setup):**
    *   *Note: If you followed the Development Setup above, you likely created a user already. This is mainly if setting up directly for production.* 
    ```bash
    cd /opt/network-monitor
    source backend/venv/bin/activate
    export FLASK_APP=backend.app:create_app
    export FLASK_CONFIG=production # Or development if appropriate
    # Ensure migrations are applied first: flask db upgrade 
    flask create-user <username> # Enter the desired username
    # You will be prompted securely for the password
    unset FLASK_APP FLASK_CONFIG
    deactivate
    ```
*   **Log In & Test Functionality.**
*   **Monitor Logs:** `sudo journalctl -u network-monitor-web -f` and `-u network-monitor-syslog -f`.

## Configuration Details

*   **Backend:** Configured via `backend/config.py` and environment variables loaded from `.env` (see `.env.example`).
*   **Frontend:** API endpoint configured in `frontend/src/services/api.js`.
*   **Deployment:** Nginx acts as reverse proxy; Gunicorn runs the Flask app; systemd manages services.

## Updating the Application

1.  Navigate to `/opt/network-monitor`.
2.  Stop services: `sudo systemctl stop network-monitor-web network-monitor-syslog`.
3.  Pull latest code: `sudo -u netmonitor git pull origin main` (or your branch).
4.  Update backend dependencies & DB:
    ```bash
    source backend/venv/bin/activate
    pip install -r requirements.txt
    export FLASK_APP=backend.app:create_app
    export FLASK_CONFIG=production
    flask db upgrade # Apply new migrations
    unset FLASK_APP FLASK_CONFIG
    deactivate
    ```
5.  Rebuild frontend (if changed):
    ```bash
    cd frontend
    # sudo -u netmonitor npm install # If package.json changed
    # sudo -u netmonitor npm run build
    cd ..
    # Fix permissions if needed
    ```
6.  Copy updated service/Nginx files if they changed.
7.  Reload & Restart:
    ```bash
    sudo systemctl daemon-reload # If service files changed
    # sudo nginx -t && sudo systemctl restart nginx # If nginx config changed
    sudo systemctl start network-monitor-web network-monitor-syslog
    ```

## Future Enhancements

*   More sophisticated UI/UX (theming, dashboard improvements, better notifications).
*   Expanded UCI configuration options.
*   REST API controller for devices.
*   Advanced log parsing/analysis.
*   Enhanced background task management (Celery).
*   Comprehensive test coverage.
*   Syslog over TCP/TLS.
*   HTTPS setup via Let's Encrypt/Certbot. 