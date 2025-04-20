#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.prod')  # Use the production env file

# Check if postgres URL is set
if 'DATABASE_URL' not in os.environ or not os.environ['DATABASE_URL'].startswith('postgresql://'):
    print("Error: DATABASE_URL environment variable not set or not configured for PostgreSQL")
    sys.exit(1)

from flask_migrate import upgrade
from app import create_app, db

print("Creating application instance...")
app = create_app()

with app.app_context():
    print("Running database migrations...")
    upgrade()
    print("Migrations complete!")
    
    print("Verifying database connection...")
    try:
        db.session.execute("SELECT 1")
        print("Database connection successful!")
    except Exception as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)
    
    print("Database setup complete!") 