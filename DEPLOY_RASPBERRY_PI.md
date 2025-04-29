select dates or user # Deploying Chore Tracker on Raspberry Pi 5

This guide provides step-by-step instructions for deploying the Chore Tracker application on a Raspberry Pi 5 with PostgreSQL as the database.

## Prerequisites

- Raspberry Pi 5 with Raspberry Pi OS installed
- Internet connection
- Basic knowledge of Linux commands

## Automatic Deployment

For automatic deployment, follow these steps:

1. Clone the repository to your Raspberry Pi:
   ```
   git clone <your-repo-url>
   cd chore-tracker
   ```

2. Make the deployment script executable:
   ```
   chmod +x deploy_pi.sh
   ```

3. Run the deployment script:
   ```
   ./deploy_pi.sh
   ```

4. After the script completes, run the database migration script:
   ```
   source venv/bin/activate
   python migrate_to_postgres.py
   ```

5. Verify the application is running:
   ```
   sudo systemctl status chore-tracker.service
   ```

## Manual Deployment

If you prefer to deploy manually or need to troubleshoot, follow these steps:

### 1. Install Dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv postgresql postgresql-contrib libpq-dev nginx
```

### 2. Set Up PostgreSQL

```bash
# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql -c "CREATE USER choretracker WITH PASSWORD 'chorepwd';"
sudo -u postgres psql -c "CREATE DATABASE chore_tracker OWNER choretracker;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE chore_tracker TO choretracker;"
```

### 3. Set Up Python Environment

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

### 4. Configure Environment Variables

Create a `.env.prod` file with the following content:

```
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://choretracker:chorepwd@localhost:5432/chore_tracker

# Google Calendar API Credentials (replace with your own)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://your-raspberry-pi-ip:5001/calendar/oauth2callback
```

### 5. Run Database Migrations

```bash
source venv/bin/activate
python migrate_to_postgres.py
```

### 6. Set Up Systemd Service

Create a file at `/etc/systemd/system/chore-tracker.service` with the following content (replace the paths with your actual paths):

```
[Unit]
Description=Chore Tracker Flask Application
After=network.target postgresql.service

[Service]
User=pi
WorkingDirectory=/path/to/chore-tracker
ExecStart=/path/to/chore-tracker/venv/bin/gunicorn -w 3 -b 0.0.0.0:5001 run:app
Restart=always
Environment="FLASK_ENV=production"
EnvironmentFile=/path/to/chore-tracker/.env.prod

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable chore-tracker.service
sudo systemctl start chore-tracker.service
```

## Troubleshooting

### Check Service Status
```bash
sudo systemctl status chore-tracker.service
```

### View Application Logs
```bash
sudo journalctl -u chore-tracker.service
```

### Database Connection Issues
Ensure PostgreSQL is running:
```bash
sudo systemctl status postgresql
```

Check PostgreSQL logs:
```bash
sudo tail -f /var/log/postgresql/postgresql-*.log
```

### Firewall Configuration
Make sure port 5001 is open:
```bash
sudo ufw allow 5001/tcp
```

## Security Considerations

For production deployment, consider the following security measures:

1. Use a strong password for the PostgreSQL user
2. Configure NGINX as a reverse proxy with HTTPS
3. Set up proper firewall rules
4. Keep the system updated

## Updating the Application

To update the application:

1. Pull the latest changes:
   ```
   git pull
   ```

2. Install any new dependencies:
   ```
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Run database migrations if needed:
   ```
   python migrate_to_postgres.py
   ```

4. Restart the service:
   ```
   sudo systemctl restart chore-tracker.service
   ``` 