#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration Variables ---
# Adjust these as needed
APP_USER="netmonitor"        # Dedicated user to run the application
APP_GROUP="netmonitor"       # Dedicated group for the user
APP_DIR="/opt/network-monitor" # Directory where the application code IS ALREADY PLACED
# REPO_URL="<YOUR_REPOSITORY_URL>" # !!! No longer needed if script run from existing code !!!
# BRANCH="main"                  # !!! No longer needed !!!

# --- Helper Functions ---
echo_info() {
    echo "[INFO] $1"
}

echo_warning() {
    echo "[WARNING] $1"
}

echo_error() {
    echo "[ERROR] $1" >&2
}

# --- Check Root ---
if [ "$(id -u)" -ne 0 ]; then
    echo_error "This script must be run as root or with sudo."
    exit 1
fi

# --- Check if running from expected source directory --- 
if [ ! -f "./requirements.txt" ] || [ ! -d "./backend" ] || [ ! -d "./frontend" ]; then
    echo_error "Script doesn't seem to be running from the project root directory."
    echo_error "Please 'cd' into the Network_Monitor project directory and run from there."
    exit 1
fi
SOURCE_DIR=$(pwd)
echo_info "Running installation from source directory: $SOURCE_DIR"

# --- Remove check for existing APP_DIR contents ---
# if [ ! -d "$APP_DIR" ] || [ ! -f "$APP_DIR/requirements.txt" ]; then
#     echo_error "Application directory '$APP_DIR' not found or doesn't contain expected files."
#     echo_error "Please ensure the project code is placed in '$APP_DIR' before running this script."
#     exit 1
# fi
# echo_info "Script assumes application code is already present in '$APP_DIR'"


# --- 1. System Preparation ---
echo_info "Updating system packages..."
apt update && apt upgrade -y

echo_info "Installing prerequisites (Python, Pip, Venv, Git, Nginx, Node.js, npm)..."
apt install -y python3 python3-pip python3-venv git nginx curl nodejs npm build-essential
# Optional: For PostgreSQL (Recommended for Production)
apt install -y postgresql postgresql-contrib libpq-dev

echo_info "Creating dedicated user '$APP_USER'..."
if id "$APP_USER" &>/dev/null; then
    echo_warning "User '$APP_USER' already exists. Skipping creation."
else
    adduser --disabled-password --gecos "" "$APP_USER"
fi
# Ensure group exists and add user if different group name desired (using same name here)
# if ! getent group "$APP_GROUP" >/dev/null; then
#    addgroup --system "$APP_GROUP"
# fi
# usermod -a -G "$APP_GROUP" "$APP_USER"

echo_info "Adding user '$APP_USER' to 'www-data' group for Nginx socket access..."
usermod -aG www-data "$APP_USER"

# --- 2. Deploy Application Code ---
echo_info "Creating application directory '$APP_DIR' (if it doesn't exist)..."
mkdir -p "$APP_DIR"

echo_info "Copying project files from $SOURCE_DIR to $APP_DIR..."
# Use rsync for efficient copy and permission handling potential
# Exclude .git directory and potentially other dev-specific files if needed
rsync -a --exclude='.git' --exclude='backend/venv' --exclude='frontend/node_modules' --exclude='backend/data/app.db' "$SOURCE_DIR/" "$APP_DIR/"

echo_info "Ensuring correct ownership for '$APP_DIR'..."
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# --- Remove Git Clone command --- 
# echo_info "Cloning repository '$REPO_URL' (branch: $BRANCH) into '$APP_DIR'..."
# sudo -u "$APP_USER" git clone -b "$BRANCH" "$REPO_URL" "$APP_DIR" || { echo_error "Failed to clone repository. Check URL and permissions."; exit 1; }

# --- 3. Backend Setup ---
echo_info "Setting up backend Python environment..."
sudo -u "$APP_USER" python3 -m venv "$APP_DIR/backend/venv"

echo_info "Installing Python dependencies..."
sudo -u "$APP_USER" "$APP_DIR/backend/venv/bin/pip" install --upgrade pip
sudo -u "$APP_USER" "$APP_DIR/backend/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo_info "Installing Gunicorn..."
sudo -u "$APP_USER" "$APP_DIR/backend/venv/bin/pip" install gunicorn

echo_info "Configuring backend environment file (if example exists)..."
if [ -f "$APP_DIR/.env.example" ]; then
    if [ ! -f "$APP_DIR/.env" ]; then
        sudo -u "$APP_USER" cp "$APP_DIR/.env.example" "$APP_DIR/.env"
        # Set FLASK_CONFIG to production
        sed -i 's/^#*FLASK_CONFIG=.*/FLASK_CONFIG=production/' "$APP_DIR/.env"
        # Ensure correct permissions
        sudo -u "$APP_USER" chmod 600 "$APP_DIR/.env"
        echo_info "Copied .env.example to .env and set basic config."
    else
        echo_warning "File '$APP_DIR/.env' already exists. Skipping copy from example."
    fi
else
    echo_warning "File '$APP_DIR/.env.example' not found. Cannot create .env automatically."
fi

# --- Database Setup (Migrations) ---
# Note: Assumes default SQLite initially. For Postgres, ensure DB exists and DATABASE_URL is set in .env first.
echo_info "Applying database migrations..."
# Ensure data directory exists if using default SQLite
sudo -u "$APP_USER" mkdir -p "$APP_DIR/backend/data"
# Run migrations as the APP_USER
sudo -u "$APP_USER" bash -c "export FLASK_APP=backend.app:create_app; export FLASK_CONFIG=production; cd $APP_DIR && backend/venv/bin/flask db upgrade"

# --- 4. Frontend Build ---
echo_info "Setting up frontend..."
echo_info "Installing frontend dependencies..."
# Running npm install/build as APP_USER to avoid permission issues
sudo -u "$APP_USER" npm --prefix "$APP_DIR/frontend" install

echo_info "Building frontend static files..."
sudo -u "$APP_USER" npm --prefix "$APP_DIR/frontend" run build

# --- 5. Configure System Services (systemd) ---
echo_warning "If you intend to use the built-in syslog listener on port 514, the system's rsyslog service must be disabled."
read -p "Do you want to disable the system rsyslog service? (y/N): " disable_rsyslog
if [[ "$disable_rsyslog" =~ ^[Yy]$ ]]; then
    echo_info "Stopping and disabling system rsyslog..."
    systemctl stop rsyslog || echo_warning "Failed to stop rsyslog (maybe not running?)."
    systemctl disable rsyslog || echo_warning "Failed to disable rsyslog."
else
    echo_info "Skipping system rsyslog disable. Ensure port 514 (or configured port) is free."
fi

echo_info "Configuring systemd service files (in source directory)..."
# Replace placeholders in the SOURCE service files
# Use pipe '|' as separator in sed for paths
sed -i -e "s|/opt/network-monitor|$APP_DIR|g" \
       -e "s/User=netmonitor/User=$APP_USER/g" \
       -e "s/Group=netmonitor/Group=$APP_USER/g" \
       "$SOURCE_DIR/network-monitor-web.service" "$SOURCE_DIR/network-monitor-syslog.service"
# Or simply use relative paths since we check PWD at the start:
# sed -i -e "s|/opt/network-monitor|$APP_DIR|g" \
#        -e "s/User=netmonitor/User=$APP_USER/g" \
#        -e "s/Group=netmonitor/Group=$APP_USER/g" \
#        ./network-monitor-web.service ./network-monitor-syslog.service

echo_info "Copying systemd service files to /etc/systemd/system/..."
# Copy the modified SOURCE files to the system directory
cp "$SOURCE_DIR/network-monitor-web.service" /etc/systemd/system/
cp "$SOURCE_DIR/network-monitor-syslog.service" /etc/systemd/system/

echo_info "Reloading systemd, enabling and starting services..."
systemctl daemon-reload
systemctl enable --now network-monitor-web.service
systemctl enable --now network-monitor-syslog.service

# --- 6. Configure Web Server (Nginx) ---
echo_info "Configuring Nginx (in source directory)..."
# Replace placeholders in the SOURCE Nginx config file
sed -i "s|/opt/network-monitor|$APP_DIR|g" "$SOURCE_DIR/network-monitor-nginx.conf"
# Or relative:
# sed -i "s|/opt/network-monitor|$APP_DIR|g" ./network-monitor-nginx.conf

echo_info "Copying Nginx configuration to /etc/nginx/sites-available/..."
# Copy the modified SOURCE file to the Nginx directory
cp "$SOURCE_DIR/network-monitor-nginx.conf" "/etc/nginx/sites-available/network-monitor"

echo_info "Enabling Nginx site and disabling default..."
ln -sf "/etc/nginx/sites-available/network-monitor" "/etc/nginx/sites-enabled/"
rm -f /etc/nginx/sites-enabled/default

echo_info "Testing Nginx configuration..."
nginx -t

echo_info "Restarting Nginx..."
systemctl restart nginx

# --- 7. Final Steps & Reminders ---
echo_info "-----------------------------------------------------------------------"
echo_info "Network Monitor Hub Installation Script Completed!"
echo_info "-----------------------------------------------------------------------"
echo_warning "** MANUAL STEPS REQUIRED: **"
echo_warning "1. **Setup PostgreSQL Database (If using PostgreSQL):**"
echo_warning "   - The PostgreSQL packages have been installed. Now, create the database and user."
echo_warning "   - Log in to PostgreSQL: 'sudo -u postgres psql'"
echo_warning "   - Inside psql, run the following (replace 'your_password' with a strong password):"
echo_warning "     CREATE DATABASE network_monitor_db;"
echo_warning "     CREATE USER netmonitor_user WITH PASSWORD 'your_password';"
echo_warning "     GRANT ALL PRIVILEGES ON DATABASE network_monitor_db TO netmonitor_user;"
echo_warning "     \q  (to exit psql)"
echo_warning "2. **Edit Environment File:**"
echo_warning "   - Open '$APP_DIR/.env' with a text editor (e.g., 'sudo nano $APP_DIR/.env')."
echo_warning "   - **Configure DATABASE_URL:** Set it to use the database you just created, e.g.:"
echo_warning "     'DATABASE_URL=postgresql://netmonitor_user:your_password@localhost/network_monitor_db'"
echo_warning "   - **Generate and set a strong SECRET_KEY.**"
echo_warning "   - **Generate and set a unique ENCRYPTION_KEY.** You can use:"
echo_warning "     'sudo -u $APP_USER $APP_DIR/backend/venv/bin/python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"'"
echo_warning "   - Configure AI_ENGINE_* variables if using the AI push feature."
echo_warning "   - Ensure SYSLOG_SERVER_IP is correct if enabling remote logging on devices."
echo_warning "   - **Restart services after editing:** 'sudo systemctl restart network-monitor-web network-monitor-syslog'"
echo_warning "3. **Configure Nginx:**"
echo_warning "   - Edit '/etc/nginx/sites-available/network-monitor'."
echo_warning "   - Change 'YOUR_SERVER_IP_OR_HOSTNAME' to your server's actual IP or domain name."
echo_warning "   - **Set up HTTPS (Recommended):** Use Certbot/Let's Encrypt."
echo_warning "   - Test and restart Nginx: 'sudo nginx -t && sudo systemctl restart nginx'"
echo_warning "4. **Configure Firewall:**"
echo_warning "   - Ensure ports are open (e.g., 80/HTTP, 443/HTTPS, 5432/PostgreSQL if needed remotely, and the Syslog UDP port)."
echo_warning "   - Example using ufw: 'sudo ufw allow 80/tcp', 'sudo ufw allow 443/tcp', 'sudo ufw allow 514/udp' (Adjust syslog port)"
echo_warning "5. **Review Admin User:**"
echo_info    "   - The default admin user ('admin'/'admin') was created automatically."
echo_warning "   - **IMPORTANT:** Log in as 'admin' and change the password immediately using the Settings page."
echo_warning "   - You can manually create other users using 'flask create-user <username>'."
echo_warning "6. **Configure OpenWRT Devices:**"
echo_warning "   - Point remote syslog to this server's IP on the configured UDP port."
echo_info "Access the web UI at: http://<YOUR_SERVER_IP_OR_HOSTNAME>"
echo_info "-----------------------------------------------------------------------"

# Make sure the socket file doesn't exist from previous failed attempts
sudo rm -f /tmp/network-monitor.sock

# Run gunicorn directly as the netmonitor user
sudo -u netmonitor /opt/network-monitor/backend/venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/tmp/network-monitor.sock \
    -m 007 \
    --chdir /opt/network-monitor \
    wsgi:app

exit 0 