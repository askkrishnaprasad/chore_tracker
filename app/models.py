from flask_login import UserMixin
from datetime import datetime
from app import db

class Home(db.Model):
    __tablename__ = 'homes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    
    users = db.relationship('User', backref='home', lazy=True)
    chores = db.relationship('Chore', backref='home', lazy=True)

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    home_id = db.Column(db.Integer, db.ForeignKey('homes.id'), nullable=True)
    
    completed_chores = db.relationship('ChoreCompletion', backref='user', lazy=True)
    assignments_given = db.relationship('ChoreAssignment', 
                                        foreign_keys='ChoreAssignment.assigner_id',
                                        backref='assigner', 
                                        lazy=True)
    assignments_received = db.relationship('ChoreAssignment', 
                                           foreign_keys='ChoreAssignment.assignee_id',
                                           backref='assignee', 
                                           lazy=True)
    calendar_token = db.relationship('UserCalendarToken', 
                                     backref='user', 
                                     lazy=True, 
                                     uselist=False)
    # New relationships
    created_chores = db.relationship('ChoreHistory', 
                                    foreign_keys='ChoreHistory.creator_id',
                                    backref='creator', 
                                    lazy=True)
    challenges_initiated = db.relationship('ChoreChallenge', 
                                          foreign_keys='ChoreChallenge.challenger_id',
                                          backref='challenger', 
                                          lazy=True)
    challenges_received = db.relationship('ChoreChallenge', 
                                         foreign_keys='ChoreChallenge.challenged_id',
                                         backref='challenged', 
                                         lazy=True)

class Chore(db.Model):
    __tablename__ = 'chores'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    home_id = db.Column(db.Integer, db.ForeignKey('homes.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    completions = db.relationship('ChoreCompletion', backref='chore', lazy=True)
    assignments = db.relationship('ChoreAssignment', backref='chore', lazy=True)
    history = db.relationship('ChoreHistory', backref='chore', lazy=True)
    challenges = db.relationship('ChoreChallenge', backref='chore', lazy=True)
    
    def __repr__(self):
        return f'<Chore {self.name}>'

class ChoreHistory(db.Model):
    """Records when chores are created and by whom"""
    __tablename__ = 'chore_history'
    id = db.Column(db.Integer, primary_key=True)
    chore_id = db.Column(db.Integer, db.ForeignKey('chores.id'), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    creation_date = db.Column(db.DateTime, default=datetime.utcnow)
    action = db.Column(db.String(50), nullable=False, default='created')  # created, edited, deleted
    previous_name = db.Column(db.String(100), nullable=True)  # For tracking changes
    
    def __repr__(self):
        return f'<ChoreHistory {self.action} {self.chore_id} by {self.creator_id}>'

class ChoreCompletion(db.Model):
    __tablename__ = 'chore_completions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    chore_id = db.Column(db.Integer, db.ForeignKey('chores.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    percentage = db.Column(db.Float, nullable=False, default=1.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')  # active, challenged, adjusted
    
    # Relationships to challenges
    challenges = db.relationship('ChoreChallenge', backref='completion', lazy=True)
    
    def __repr__(self):
        return f'<ChoreCompletion {self.chore_id} by {self.user_id} ({self.percentage*100}%)>'

class ChoreChallenge(db.Model):
    """Records challenges to chore completions"""
    __tablename__ = 'chore_challenges'
    id = db.Column(db.Integer, primary_key=True)
    completion_id = db.Column(db.Integer, db.ForeignKey('chore_completions.id'), nullable=False)
    chore_id = db.Column(db.Integer, db.ForeignKey('chores.id'), nullable=False)
    challenger_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    challenged_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    challenge_date = db.Column(db.DateTime, default=datetime.utcnow)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, defended, rejected
    resolution_date = db.Column(db.DateTime, nullable=True)
    
    # Defense and resolution details
    defense_comment = db.Column(db.Text, nullable=True)
    adjustment_percentage = db.Column(db.Float, nullable=True)  # New percentage if adjusted
    
    def __repr__(self):
        return f'<ChoreChallenge on {self.completion_id} - {self.status}>'

class ChoreAssignment(db.Model):
    __tablename__ = 'chore_assignments'
    id = db.Column(db.Integer, primary_key=True)
    assigner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    chore_id = db.Column(db.Integer, db.ForeignKey('chores.id'), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    points = db.Column(db.Float, nullable=False, default=1.0)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, completed, missed
    penalty_points = db.Column(db.Float, default=0.0)
    
    def __repr__(self):
        return f'<ChoreAssignment {self.chore_id} to {self.assignee_id}>'

class UserCalendarToken(db.Model):
    __tablename__ = 'user_calendar_tokens'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text, nullable=True)
    token_expiry = db.Column(db.DateTime, nullable=True) 

class UserActivity(db.Model):
    """Tracks user activity in the application"""
    __tablename__ = 'user_activity'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # login, view_chores, complete_chore, etc.
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    page = db.Column(db.String(50), nullable=True)  # which page the action occurred on
    details = db.Column(db.Text, nullable=True)  # additional details (JSON)
    
    # Relationship to user
    user = db.relationship('User', backref=db.backref('activities', lazy=True))
    
    def __repr__(self):
        return f'<UserActivity {self.user_id} {self.action} {self.timestamp}>' 