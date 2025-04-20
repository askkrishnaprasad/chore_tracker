#!/bin/bash

# Deployment script for Chore Tracker on Raspberry Pi 5
echo "Starting deployment of Chore Tracker..."

# Update system packages
echo "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required dependencies
echo "Installing dependencies..."
sudo apt install -y python3-pip python3-venv postgresql postgresql-contrib libpq-dev nginx

# Create Python virtual environment
echo "Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python requirements..."
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# Set up PostgreSQL
echo "Setting up PostgreSQL database..."
sudo -u postgres psql -c "CREATE USER choretracker WITH PASSWORD 'chorepwd';"
sudo -u postgres psql -c "CREATE DATABASE chore_tracker OWNER choretracker;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE chore_tracker TO choretracker;"

# Create production .env file
echo "Creating production environment file..."
cat > .env.prod << EOL
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(16))")
DATABASE_URL=postgresql://choretracker:chorepwd@localhost:5432/chore_tracker

# Google Calendar API Credentials (replace with your own values)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://your-raspberry-pi-ip:5001/calendar/oauth2callback
EOL

# Set up systemd service
echo "Setting up systemd service..."
sudo bash -c 'cat > /etc/systemd/system/chore-tracker.service << EOL
[Unit]
Description=Chore Tracker Flask Application
After=network.target postgresql.service

[Service]
User=pi
WorkingDirectory='$(pwd)'
ExecStart='$(pwd)'/venv/bin/gunicorn -w 3 -b 0.0.0.0:5001 run:app
Restart=always
Environment="FLASK_ENV=production"
EnvironmentFile='$(pwd)'/.env.prod

[Install]
WantedBy=multi-user.target
EOL'

# Enable and start the service
echo "Enabling and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable chore-tracker.service
sudo systemctl start chore-tracker.service

# Final instructions
echo "Deployment complete!"
echo "The application should be running on port 5001"
echo "Check service status with: sudo systemctl status chore-tracker.service"
echo "View logs with: sudo journalctl -u chore-tracker.service" 