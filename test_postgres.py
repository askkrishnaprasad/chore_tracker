#!/usr/bin/env python3
import os
import sys
import psycopg2
from dotenv import load_dotenv

def test_postgres_connection():
    # Try to load production env first, fall back to regular .env
    if os.path.exists('.env.prod'):
        load_dotenv('.env.prod')
    else:
        load_dotenv()
    
    # Get database URL
    db_url = os.environ.get('DATABASE_URL')
    if not db_url or not db_url.startswith('postgresql://'):
        print("Error: DATABASE_URL environment variable not set or not configured for PostgreSQL")
        sys.exit(1)
    
    print(f"Testing connection to PostgreSQL...")
    
    try:
        # Parse the connection string
        # Format: postgresql://user:password@host:port/dbname
        db_parts = db_url.replace('postgresql://', '').split('@')
        user_pass = db_parts[0].split(':')
        host_port_db = db_parts[1].split('/')
        
        user = user_pass[0]
        password = user_pass[1] if len(user_pass) > 1 else ''
        
        host_port = host_port_db[0].split(':')
        host = host_port[0]
        port = int(host_port[1]) if len(host_port) > 1 else 5432
        
        dbname = host_port_db[1]
        
        # Connect to the database
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        
        # Create a cursor
        cur = conn.cursor()
        
        # Execute a test query
        cur.execute("SELECT version();")
        
        # Get the result
        version = cur.fetchone()
        print(f"Connection successful! PostgreSQL version: {version[0]}")
        
        # Close the cursor and connection
        cur.close()
        conn.close()
        print("Connection closed.")
        return True
        
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        return False

if __name__ == "__main__":
    if test_postgres_connection():
        sys.exit(0)
    else:
        sys.exit(1) 