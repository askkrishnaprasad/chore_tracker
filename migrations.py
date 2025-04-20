from flask_migrate import Migrate
from app import create_app, db

app = create_app()
migrate = Migrate(app, db)

if __name__ == '__main__':
    print("Migration setup complete. Use 'flask db init', 'flask db migrate', and 'flask db upgrade' commands to manage migrations.") 