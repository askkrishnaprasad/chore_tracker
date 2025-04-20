from app import create_app, db
from app.models import User, Home, Chore, ChoreHistory, ChoreCompletion, ChoreChallenge, ChoreAssignment, UserActivity
from werkzeug.security import generate_password_hash
import os
from datetime import datetime, timedelta
import random
import sys

def init_db(load_sample_activity=False):
    app = create_app()
    with app.app_context():
        # Drop all existing tables
        print("Dropping all existing tables...")
        db.drop_all()
        
        # Create tables
        print("Creating new tables...")
        db.create_all()
        
        # Create admin user
        print("Creating admin user...")
        admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        
        # Create admin user
        admin = User(
            username=admin_username,
            password_hash=generate_password_hash(admin_password),
            is_admin=True
        )
        
        db.session.add(admin)
        db.session.commit()
        
        print(f"Admin user created with username: {admin_username}")
        print("Please change the default password after logging in!")
        
        # Create a default home
        print("Creating default home...")
        home = Home(name="Default Home")
        db.session.add(home)
        db.session.commit()
        
        # Create a regular user for the home
        print("Creating a regular user...")
        user = User(
            username="user",
            password_hash=generate_password_hash("user123"),
            is_admin=False,
            home_id=home.id
        )
        db.session.add(user)
        db.session.commit()
        
        # Add some sample chores with history
        sample_chores = [
            "Wash Dishes",
            "Vacuum Living Room",
            "Take Out Trash",
            "Mow the Lawn",
            "Clean Bathroom",
            "Laundry"
        ]
        
        print("Adding sample chores with history...")
        for chore_name in sample_chores:
            # Create the chore
            chore = Chore(
                name=chore_name, 
                home_id=home.id,
                created_at=datetime.utcnow(),
                is_active=True
            )
            db.session.add(chore)
            db.session.flush()  # Flush to get the chore ID
            
            # Create chore history entry
            history = ChoreHistory(
                chore_id=chore.id,
                creator_id=admin.id,
                creation_date=datetime.utcnow(),
                action="created"
            )
            db.session.add(history)
        
        db.session.commit()
        print(f"Default home created with {len(sample_chores)} sample chores.")
        
        # Add a sample chore completion
        print("Adding sample chore completions...")
        chore = Chore.query.first()
        completion = ChoreCompletion(
            user_id=user.id,
            chore_id=chore.id,
            date=datetime.utcnow().date(),
            percentage=1.0,
            status="active"
        )
        db.session.add(completion)
        
        # Add a sample chore assignment
        print("Adding sample chore assignments...")
        chore = Chore.query.offset(1).first()  # Get the second chore
        assignment = ChoreAssignment(
            assigner_id=admin.id,
            assignee_id=user.id,
            chore_id=chore.id,
            due_date=datetime.utcnow().date(),
            points=1.0,
            notes="Please complete this assigned chore",
            status="pending"
        )
        db.session.add(assignment)
        
        db.session.commit()
        print("Added sample completions and assignments.")
        
        # Only add sample activity data if explicitly requested
        if load_sample_activity:
            # Add sample user activity data
            print("Adding sample user activity data...")
            # Get user ids
            users = User.query.all()
            user_ids = [user.id for user in users]
            
            # Actions to track
            actions = ['login', 'visit', 'complete_chore', 'add_chore', 'view_chores', 'assign_chore']
            pages = ['login_page', 'dashboard', 'chores', 'add_chore', 'chore_history', 'assign_chore']
            
            # Generate activity for the past 30 days
            today = datetime.utcnow()
            
            for day_offset in range(30, -1, -1):
                day = today - timedelta(days=day_offset)
                # More activity for recent days, less for older days
                activity_count = int(10 + (30 - day_offset) * 1.5)
                
                for _ in range(activity_count):
                    user_id = random.choice(user_ids)
                    action = random.choice(actions)
                    page = random.choice(pages)
                    
                    # Randomize time within the day
                    hour = random.randint(8, 22)  # Between 8 AM and 10 PM
                    minute = random.randint(0, 59)
                    second = random.randint(0, 59)
                    activity_time = day.replace(hour=hour, minute=minute, second=second)
                    
                    activity = UserActivity(
                        user_id=user_id,
                        action=action,
                        page=page,
                        timestamp=activity_time,
                        details="{}"
                    )
                    
                    db.session.add(activity)
            
            db.session.commit()
            print("Added sample user activity data.")
        else:
            print("Skipping sample activity data generation.")

if __name__ == "__main__":
    # Check if sample activity data should be loaded
    load_sample = "--with-sample-activity" in sys.argv
    
    init_db(load_sample_activity=load_sample)
    
    if load_sample:
        print("Database initialization complete with sample activity data!")
    else:
        print("Database initialization complete! (No sample activity data)")
        print("To include sample activity data, run with: python init_db.py --with-sample-activity") 