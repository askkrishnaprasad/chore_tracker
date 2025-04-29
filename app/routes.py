from flask import render_template, redirect, url_for, flash, request, jsonify, session, send_file
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User, Home, Chore, ChoreCompletion, ChoreAssignment, UserCalendarToken, ChoreHistory, ChoreChallenge, UserActivity
from app.forms import (LoginForm, RegistrationForm, HomeForm, ChoreForm, 
                   ChoreCompletionForm, ChoreAssignmentForm, UserForm)
from app import db, login_manager
from datetime import date, datetime, timedelta, time
from sqlalchemy import func, and_
import json
from app.google_calendar import get_authorization_url, process_oauth_callback, save_tokens, add_calendar_event
import io
import os
import xlsxwriter
import pytz

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper function to track user activity
def track_activity(user_id, action, page=None, details=None):
    activity = UserActivity(
        user_id=user_id,
        action=action,
        page=page,
        details=json.dumps(details) if details else None
    )
    db.session.add(activity)
    try:
        db.session.commit()
    except:
        db.session.rollback()

def register_routes(app):
    
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('index.html')
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user and check_password_hash(user.password_hash, form.password.data):
                login_user(user, remember=form.remember.data)
                # Track login activity
                track_activity(user.id, 'login', 'login_page', {
                    'user_agent': request.headers.get('User-Agent'),
                    'ip': request.remote_addr
                })
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard'))
            else:
                flash('Login unsuccessful. Please check username and password', 'danger')
        
        return render_template('login.html', form=form)
    
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        form = RegistrationForm()
        if form.validate_on_submit():
            # Check if username already exists
            existing_user = User.query.filter_by(username=form.username.data).first()
            if existing_user:
                flash(f'Username "{form.username.data}" is already taken. Please choose another.', 'danger')
                return render_template('register.html', form=form)
                
            # Check if this is the first user (will be global admin)
            is_first_user = User.query.count() == 0
            
            hashed_password = generate_password_hash(form.password.data)
            user = User(username=form.username.data, 
                        password_hash=hashed_password,
                        is_admin=is_first_user)
            
            try:
                db.session.add(user)
                db.session.commit()
                flash(f'Account created for {form.username.data}!', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                db.session.rollback()
                flash('An error occurred while creating your account. Please try again.', 'danger')
                app.logger.error(f"Error during registration: {str(e)}")
        
        return render_template('register.html', form=form)
    
    @app.route('/logout')
    def logout():
        logout_user()
        return redirect(url_for('index'))
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        # Track dashboard visit
        track_activity(current_user.id, 'visit', 'dashboard')
        
        if current_user.is_admin and not current_user.home_id:
            # Global admin dashboard
            total_users = User.query.count()
            total_homes = Home.query.count()
            total_chores = Chore.query.count()
            total_completions = ChoreCompletion.query.count()
            
            # Get some basic activity stats
            today = datetime.now().date()
            start_of_today = datetime.combine(today, datetime.min.time())
            
            # Daily active users (unique users with activity today)
            daily_active_users = db.session.query(UserActivity.user_id).distinct().filter(
                UserActivity.timestamp >= start_of_today
            ).count()
            
            # Weekly active users
            week_ago = today - timedelta(days=7)
            start_of_week = datetime.combine(week_ago, datetime.min.time())
            weekly_active_users = db.session.query(UserActivity.user_id).distinct().filter(
                UserActivity.timestamp >= start_of_week
            ).count()
            
            # Monthly active users
            month_ago = today - timedelta(days=30)
            start_of_month = datetime.combine(month_ago, datetime.min.time())
            monthly_active_users = db.session.query(UserActivity.user_id).distinct().filter(
                UserActivity.timestamp >= start_of_month
            ).count()
            
            # Get recent activities 
            recent_activities = UserActivity.query.order_by(
                UserActivity.timestamp.desc()
            ).limit(10).all()
            
            recent_activity_data = []
            for activity in recent_activities:
                user = User.query.get(activity.user_id)
                if user:
                    recent_activity_data.append({
                        'user': user.username,
                        'action': activity.action,
                        'timestamp': activity.timestamp,
                        'page': activity.page
                    })
            
            return render_template('admin_dashboard.html', 
                                  total_users=total_users, 
                                  total_homes=total_homes,
                                  total_chores=total_chores,
                                  total_completions=total_completions,
                                  daily_active_users=daily_active_users,
                                  weekly_active_users=weekly_active_users,
                                  monthly_active_users=monthly_active_users,
                                  recent_activities=recent_activity_data,
                                  homes=Home.query.all())
        
        # Check if user has a home assigned
        if not current_user.home_id:
            flash('You are not assigned to a home yet. Please contact an admin to get assigned to a home.', 'warning')
            return render_template('no_home.html')
            
        # Regular user dashboard
        # Get user's home
        home = Home.query.get(current_user.home_id)
        
        # Additional check to ensure home exists
        if not home:
            flash('Your assigned home could not be found. Please contact an admin to fix this issue.', 'danger')
            return render_template('no_home.html')
            
        # Get all users in this home
        home_users = User.query.filter_by(home_id=home.id).all()
        
        # Today's chores
        today = datetime.now().date()
        today_chores = ChoreCompletion.query.join(Chore).filter(
            ChoreCompletion.user_id.in_([user.id for user in home_users]),
            ChoreCompletion.date == today,
            Chore.home_id == home.id
        ).order_by(ChoreCompletion.id.desc()).all()
        
        # Pending assignments for current user
        # Include all pending assignments regardless of whether the current user assigned them to themselves
        pending_assignments = ChoreAssignment.query.join(Chore).filter(
            ChoreAssignment.assignee_id == current_user.id,
            ChoreAssignment.status == 'pending',
            Chore.home_id == home.id
        ).order_by(ChoreAssignment.due_date).all()
        
        # User stats
        user_stats = {}
        
        # Weekly data for chart
        seven_days_ago = today - timedelta(days=6)
        date_labels = [(seven_days_ago + timedelta(days=i)).strftime('%a') for i in range(7)]
        
        datasets = []
        colors = ['rgba(78, 115, 223, 0.8)', 'rgba(28, 200, 138, 0.8)', 'rgba(54, 185, 204, 0.8)', 
                  'rgba(246, 194, 62, 0.8)', 'rgba(231, 74, 59, 0.8)', 'rgba(111, 66, 193, 0.8)']
        
        for i, user in enumerate(home_users):
            user_stats[user.id] = {'total_points': 0, 'daily_points': {}}
            color_idx = i % len(colors)
            
            # Initialize daily points
            for day in range(7):
                date = seven_days_ago + timedelta(days=day)
                user_stats[user.id]['daily_points'][date.strftime('%Y-%m-%d')] = 0
            
            # Get user's completions
            completions = ChoreCompletion.query.filter(
                ChoreCompletion.user_id == user.id,
                ChoreCompletion.date >= seven_days_ago,
                ChoreCompletion.date <= today
            ).all()
            
            # Total all completions
            all_completions = ChoreCompletion.query.filter(
                ChoreCompletion.user_id == user.id
            ).all()
            
            for completion in all_completions:
                user_stats[user.id]['total_points'] += completion.percentage
            
            # Process completions within the last 7 days
            for completion in completions:
                date_str = completion.date.strftime('%Y-%m-%d')
                if date_str in user_stats[user.id]['daily_points']:
                    user_stats[user.id]['daily_points'][date_str] += completion.percentage
            
            # Create the dataset for this user
            daily_data = [user_stats[user.id]['daily_points'].get((seven_days_ago + timedelta(days=i)).strftime('%Y-%m-%d'), 0) 
                         for i in range(7)]
            
            datasets.append({
                'label': user.username,
                'data': daily_data,
                'backgroundColor': colors[color_idx],
                'borderColor': colors[color_idx].replace('0.8', '1'),
                'borderWidth': 2,
                'pointBackgroundColor': colors[color_idx].replace('0.8', '1'),
                'tension': 0.3
            })
        
        # Prepare chart data
        weekly_chart_data = {
            'labels': date_labels,
            'datasets': datasets
        }
        
        # Monthly chart data
        first_day_of_month = today.replace(day=1)
        if today.month == 12:
            last_day_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            last_day_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        
        days_in_month = (last_day_of_month - first_day_of_month).days + 1
        
        monthly_datasets = []
        for i, user in enumerate(home_users):
            color_idx = i % len(colors)
            
            # Get user's completions for the month
            monthly_completions = ChoreCompletion.query.filter(
                ChoreCompletion.user_id == user.id,
                ChoreCompletion.date >= first_day_of_month,
                ChoreCompletion.date <= last_day_of_month
            ).all()
            
            # Initialize daily points for the month
            monthly_points = {}
            for day in range(1, days_in_month + 1):
                date = first_day_of_month + timedelta(days=day-1)
                monthly_points[date.day] = 0
            
            # Process monthly completions
            for completion in monthly_completions:
                monthly_points[completion.date.day] += completion.percentage
            
            # Create dataset
            monthly_data = [monthly_points.get(day, 0) for day in range(1, days_in_month + 1)]
            
            monthly_datasets.append({
                'label': user.username,
                'data': monthly_data,
                'backgroundColor': colors[color_idx],
                'borderColor': colors[color_idx].replace('0.8', '1'),
                'borderWidth': 1
            })
        
        # Create monthly labels
        monthly_labels = [str(day) for day in range(1, days_in_month + 1)]
        
        monthly_chart_data = {
            'labels': monthly_labels,
            'datasets': monthly_datasets
        }
        
        # Yearly chart data - for total points
        yearly_data = [user_stats[user.id]['total_points'] for user in home_users]
        yearly_labels = [user.username for user in home_users]
        yearly_colors = [colors[i % len(colors)] for i in range(len(home_users))]
        
        yearly_chart_data = {
            'labels': yearly_labels,
            'datasets': [{
                'label': 'Total Points',
                'data': yearly_data,
                'backgroundColor': yearly_colors,
                'borderColor': [color.replace('0.8', '1') for color in yearly_colors],
                'borderWidth': 1
            }]
        }
        
        # Distribution chart data - which chores are done by whom
        chore_stats = {}
        home_chores = Chore.query.filter_by(home_id=home.id).all()
        
        for chore in home_chores:
            all_chore_completions = ChoreCompletion.query.filter_by(chore_id=chore.id).all()
            if not all_chore_completions:
                continue
            
            user_percentages = {}
            for user in home_users:
                user_percentages[user.id] = 0
            
            for completion in all_chore_completions:
                if completion.user_id in user_percentages:
                    user_percentages[completion.user_id] += completion.percentage
            
            # Find the dominant user (most percentage)
            dominant_user_id = max(user_percentages.items(), key=lambda x: x[1])[0] if user_percentages else None
            dominant_user = User.query.get(dominant_user_id) if dominant_user_id else None
            
            if dominant_user:
                total_percentage = sum(user_percentages.values())
                chore_stats[chore.id] = {
                    'chore': chore,
                    'dominant_user': dominant_user,
                    'count': sum(1 for c in all_chore_completions if c.user_id == dominant_user_id),
                    'total_percentage': user_percentages[dominant_user_id] / total_percentage if total_percentage > 0 else 0
                }
        
        # Distribution chart data
        user_chore_counts = {}
        for user in home_users:
            user_chore_counts[user.id] = 0
        
        for chore_id, stats in chore_stats.items():
            user_chore_counts[stats['dominant_user'].id] += 1
        
        distribution_labels = [user.username for user in home_users]
        distribution_data = [user_chore_counts.get(user.id, 0) for user in home_users]
        distribution_colors = [colors[i % len(colors)] for i in range(len(home_users))]
        
        distribution_chart_data = {
            'labels': distribution_labels,
            'datasets': [{
                'label': 'Chores Dominated',
                'data': distribution_data,
                'backgroundColor': distribution_colors,
                'borderColor': [color.replace('0.8', '1') for color in distribution_colors],
                'borderWidth': 1
            }]
        }
        
        return render_template('dashboard.html', 
                               home=home,
                               home_users=home_users,
                               today_chores=today_chores,
                               pending_assignments=pending_assignments,
                               user_stats=user_stats,
                               chore_stats=chore_stats,
                               weekly_chart_data=weekly_chart_data,
                               monthly_chart_data=monthly_chart_data,
                               yearly_chart_data=yearly_chart_data,
                               distribution_chart_data=distribution_chart_data,
                               today=today)
    
    @app.route('/chores')
    @login_required
    def chores():
        # Track chores page visit
        track_activity(current_user.id, 'visit', 'chores')
        
        if not current_user.home_id:
            flash('You need to be assigned to a home before you can view or manage chores.', 'warning')
            if current_user.is_admin:
                return redirect(url_for('admin_homes'))
            return render_template('no_home.html')
        
        chores = Chore.query.filter_by(home_id=current_user.home_id).all()
        home_users = User.query.filter_by(home_id=current_user.home_id).all()
        
        # Check for date parameter in request
        date_param = request.args.get('date')
        today = date.today()
        
        if date_param:
            try:
                # Parse the date from the parameter (format: YYYY-MM-DD)
                filter_date = datetime.strptime(date_param, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format. Using today\'s date instead.', 'warning')
                filter_date = today
        else:
            filter_date = today
            
        # Get completions for the selected date
        completed_chores = ChoreCompletion.query.filter_by(
            user_id=current_user.id, 
            date=filter_date
        ).all()
        completed_chore_ids = [c.chore_id for c in completed_chores]
        
        # Format the displayed date
        if filter_date == today:
            display_date = "Today"
            date_class = "alert-info"
        else:
            # Format the date for display
            display_date = filter_date.strftime('%A, %B %d, %Y')
            date_class = "alert-warning"
        
        return render_template('chores.html', 
                              chores=chores, 
                              home_users=home_users,
                              completed_chore_ids=completed_chore_ids,
                              today=filter_date,
                              display_date=display_date,
                              date_class=date_class)
    
    @app.route('/add_chore', methods=['GET', 'POST'])
    @login_required
    def add_chore():
        if not current_user.home_id:
            flash('You need to be assigned to a home before you can add chores.', 'warning')
            if current_user.is_admin:
                return redirect(url_for('admin_homes'))
            return render_template('no_home.html')
        
        # Track page visit on GET request
        if request.method == 'GET':
            track_activity(current_user.id, 'visit', 'add_chore')
        
        form = ChoreForm()
        if form.validate_on_submit():
            # Create new chore
            chore = Chore(
                name=form.name.data,
                home_id=current_user.home_id,
                created_at=datetime.now(),
                is_active=True
            )
            db.session.add(chore)
            db.session.flush()  # Flush to get the chore ID
            
            # Create chore history entry
            history = ChoreHistory(
                chore_id=chore.id,
                creator_id=current_user.id,
                creation_date=datetime.now(),
                action="created"
            )
            db.session.add(history)
            
            db.session.commit()
            
            # Track chore creation
            track_activity(current_user.id, 'add_chore', 'add_chore', {
                'chore_id': chore.id,
                'chore_name': chore.name,
                'home_id': current_user.home_id
            })
            
            flash(f'Chore "{form.name.data}" added!', 'success')
            return redirect(url_for('chores'))
        
        return render_template('add_chore.html', form=form)
    
    @app.route('/edit_chore', methods=['POST'])
    @login_required
    def edit_chore():
        if not current_user.home_id:
            flash('You need to be assigned to a home before you can edit chores.', 'warning')
            if current_user.is_admin:
                return redirect(url_for('admin_homes'))
            return render_template('no_home.html')
        
        chore_id = request.form.get('chore_id')
        new_name = request.form.get('name')
        
        if not chore_id or not new_name:
            flash('Invalid request.', 'danger')
            return redirect(url_for('chores'))
        
        # Find the chore and make sure it belongs to the user's home
        chore = Chore.query.filter_by(id=chore_id, home_id=current_user.home_id).first()
        
        if not chore:
            flash('Chore not found or you do not have permission to edit it.', 'danger')
            return redirect(url_for('chores'))
        
        # Store the old name for the history record
        old_name = chore.name
        
        # Update the chore name
        chore.name = new_name
        
        # Create chore history entry for the edit
        history = ChoreHistory(
            chore_id=chore.id,
            creator_id=current_user.id,
            creation_date=datetime.now(),
            action="edited",
            previous_name=old_name
        )
        db.session.add(history)
        
        db.session.commit()
        
        flash(f'Chore updated from "{old_name}" to "{new_name}"!', 'success')
        return redirect(url_for('chores'))
    
    @app.route('/chore_history')
    @login_required
    def chore_history():
        if not current_user.home_id:
            flash('You need to be assigned to a home before you can view chore history.', 'warning')
            if current_user.is_admin:
                return redirect(url_for('admin_homes'))
            return render_template('no_home.html')
        
        # Get chore history for this home
        chore_history = ChoreHistory.query.join(Chore).filter(
            Chore.home_id == current_user.home_id
        ).order_by(ChoreHistory.creation_date.desc()).all()
        
        # Get chore completions for this home
        completions = ChoreCompletion.query.join(Chore).filter(
            Chore.home_id == current_user.home_id
        ).order_by(ChoreCompletion.created_at.desc()).all()
        
        # Get pending challenges for this home
        pending_challenges = ChoreChallenge.query.join(Chore).filter(
            Chore.home_id == current_user.home_id,
            ChoreChallenge.status == 'pending'
        ).order_by(ChoreChallenge.challenge_date.desc()).all()
        
        # Get resolved challenges for this home
        resolved_challenges = ChoreChallenge.query.join(Chore).filter(
            Chore.home_id == current_user.home_id,
            ChoreChallenge.status.in_(['accepted', 'defended', 'pending_approval'])
        ).order_by(ChoreChallenge.resolution_date.desc()).all()
        
        # Get today's date for the date picker
        today = date.today().strftime('%Y-%m-%d')
        
        return render_template('chore_history.html', 
                               chore_history=chore_history,
                               completions=completions,
                               challenges=pending_challenges,
                               resolved_challenges=resolved_challenges,
                               today=today)
    
    @app.route('/challenge_chore', methods=['POST'])
    @login_required
    def challenge_chore():
        if not current_user.home_id:
            flash('You need to be assigned to a home first.', 'warning')
            return redirect(url_for('dashboard'))
        
        completion_id = request.form.get('completion_id')
        reason = request.form.get('reason')
        
        if not completion_id or not reason:
            flash('Invalid request. Please provide all required information.', 'danger')
            return redirect(url_for('chore_history'))
        
        # Get the completion
        completion = ChoreCompletion.query.get_or_404(completion_id)
        
        # Check if the chore is from the same home
        chore = Chore.query.get(completion.chore_id)
        if chore.home_id != current_user.home_id:
            flash('You can only challenge chores in your own home.', 'danger')
            return redirect(url_for('chore_history'))
        
        # Check if the completion is already challenged
        if completion.status != 'active':
            flash('This chore completion has already been challenged or adjusted.', 'warning')
            return redirect(url_for('chore_history'))
        
        # Create challenge
        challenge = ChoreChallenge(
            completion_id=completion_id,
            chore_id=completion.chore_id,
            challenger_id=current_user.id,
            challenged_id=completion.user_id,
            challenge_date=datetime.now(),
            reason=reason,
            status='pending'
        )
        
        # Update completion status
        completion.status = 'challenged'
        
        db.session.add(challenge)
        db.session.commit()
        
        flash('Challenge submitted successfully. The user will be notified to respond.', 'success')
        return redirect(url_for('chore_history'))
    
    @app.route('/defend_challenge', methods=['POST'])
    @login_required
    def defend_challenge():
        challenge_id = request.form.get('challenge_id')
        response_type = request.form.get('response_type')
        
        if not challenge_id or not response_type:
            flash('Invalid request. Please provide all required information.', 'danger')
            return redirect(url_for('chore_history'))
        
        # Get the challenge
        challenge = ChoreChallenge.query.get_or_404(challenge_id)
        
        # Check if the user is the one being challenged
        if challenge.challenged_id != current_user.id:
            flash('You can only respond to challenges directed at you.', 'danger')
            return redirect(url_for('chore_history'))
        
        # Get the completion
        completion = ChoreCompletion.query.get(challenge.completion_id)
        completion_id = completion.id
        
        # Get the chore details for notifications
        chore = Chore.query.get(completion.chore_id)
        
        if response_type == 'defend':
            defense_comment = request.form.get('defense_comment')
            if not defense_comment or defense_comment.strip() == '':
                flash('Please provide a defense comment.', 'warning')
                return redirect(url_for('chore_history'))
            
            # Update challenge
            challenge.status = 'defended'
            challenge.defense_comment = defense_comment
            challenge.resolution_date = datetime.now()
            
            # Keep the completion as is
            completion.status = 'active'
            
            flash('You have successfully defended your chore completion.', 'success')
        
        elif response_type == 'accept':
            adjustment_percentage = request.form.get('adjustment_percentage')
            if not adjustment_percentage:
                flash('Please provide an adjustment percentage.', 'warning')
                return redirect(url_for('chore_history'))
            
            try:
                adjustment_percentage = float(adjustment_percentage) / 100.0
                if adjustment_percentage < 0 or adjustment_percentage > 1:
                    raise ValueError("Percentage must be between 0 and 100")
            except ValueError:
                flash('Invalid adjustment percentage. Please enter a number between 0 and 100.', 'danger')
                return redirect(url_for('chore_history'))
            
            # Get the original percentage before adjustment
            original_percentage = completion.percentage
            
            # Store the proposed adjustment in the challenge record
            challenge.status = 'pending_approval'
            challenge.adjustment_percentage = adjustment_percentage
            challenge.defense_comment = f"User accepted challenge and proposed an adjustment to {int(adjustment_percentage * 100)}%"
            
            # The completion remains challenged until approved
            completion.status = 'challenged'
            
            # If this is a shared chore, provide detailed information in the defense comment
            other_completions = ChoreCompletion.query.filter(
                ChoreCompletion.chore_id == completion.chore_id,
                ChoreCompletion.date == completion.date,
                ChoreCompletion.id != completion.id
            ).all()
            
            if other_completions:
                other_usernames = [User.query.get(oc.user_id).username for oc in other_completions]
                
                # For single other user case
                if len(other_completions) == 1:
                    other_completion = other_completions[0]
                    # The other user gets the remaining percentage (ensuring total is 100%)
                    new_percentage = 1.0 - adjustment_percentage
                    challenge.defense_comment += f". This is a shared chore with {other_completion.user.username}. Their percentage will be adjusted from {int(other_completion.percentage * 100)}% to {int(new_percentage * 100)}% to maintain a total of 100%."
                # For multiple users case
                else:
                    remaining_percentage = 1.0 - adjustment_percentage
                    original_others_total = sum(oc.percentage for oc in other_completions)
                    
                    challenge.defense_comment += f". This is a shared chore with {', '.join(other_usernames)}. The remaining {int(remaining_percentage * 100)}% will be distributed proportionally among them based on their current percentages."
                    
                    # Add more detailed explanation about how the percentages will be adjusted
                    for oc in other_completions:
                        user = User.query.get(oc.user_id)
                        if original_others_total > 0:
                            proportion = oc.percentage / original_others_total
                            new_percentage = remaining_percentage * proportion
                            challenge.defense_comment += f"\n- {user.username}'s percentage will change from {int(oc.percentage * 100)}% to approximately {int(new_percentage * 100)}%."
            
            flash('You have accepted the challenge and proposed an adjustment. Waiting for challenger approval.', 'success')
        
        else:
            flash('Invalid response type.', 'danger')
            return redirect(url_for('chore_history'))
        
        # Mark all other pending challenges for this completion as auto-resolved
        other_challenges = ChoreChallenge.query.filter(
            ChoreChallenge.completion_id == completion_id,
            ChoreChallenge.id != challenge.id,
            ChoreChallenge.status == 'pending'
        ).all()
        
        for other_challenge in other_challenges:
            other_challenge.status = 'auto_resolved'
            other_challenge.resolution_date = datetime.now()
            other_challenge.defense_comment = f"Auto-resolved because another challenge for this completion was already {challenge.status}."
        
        db.session.commit()
        return redirect(url_for('chore_history'))
    
    @app.route('/complete_chore', methods=['POST'])
    @login_required
    def complete_chore():
        form = ChoreCompletionForm()
        form.user_id.data = current_user.id
        
        # Set the choices for the other_user_id field
        if current_user.home_id:
            home_users = User.query.filter_by(home_id=current_user.home_id).all()
            form.other_user_id.choices = [(u.id, u.username) for u in home_users if u.id != current_user.id]
        
        # Check if we should redirect back to dashboard
        redirect_to = request.form.get('redirect_to', 'chores')
        
        if form.validate_on_submit():
            # Get the selected date from the form
            completion_date = form.completion_date.data
            
            # Check if chore was already completed on the selected date
            existing = ChoreCompletion.query.filter_by(
                user_id=current_user.id,
                chore_id=form.chore_id.data,
                date=completion_date
            ).first()
            
            if existing:
                flash(f'You already completed this chore on {completion_date.strftime("%b %d, %Y")}!', 'warning')
                return redirect(url_for(redirect_to))
            
            # Calculate percentage based on sharing option
            percentage = 1.0  # Default: 100%
            
            if form.is_shared.data:
                percentage = form.percentage.data / 100
                # Create completion record for other user
                other_user_completion = ChoreCompletion(
                    user_id=form.other_user_id.data,
                    chore_id=form.chore_id.data,
                    date=completion_date,
                    percentage=1.0 - percentage,
                    created_at=datetime.now(),
                    status='active'
                )
                db.session.add(other_user_completion)
            
            # Create completion record for current user
            completion = ChoreCompletion(
                user_id=current_user.id,
                chore_id=form.chore_id.data,
                date=completion_date,
                percentage=percentage,
                created_at=datetime.now(),
                status='active'
            )
            
            db.session.add(completion)
            db.session.commit()
            
            # Track chore completion
            chore = Chore.query.get(form.chore_id.data)
            track_activity(current_user.id, 'complete_chore', redirect_to, {
                'chore_id': form.chore_id.data,
                'chore_name': chore.name,
                'date': completion_date.strftime('%Y-%m-%d'),
                'percentage': percentage,
                'is_shared': form.is_shared.data
            })
            
            # If shared, track for the other user as well
            if form.is_shared.data:
                track_activity(form.other_user_id.data, 'assigned_completion', redirect_to, {
                    'chore_id': form.chore_id.data,
                    'chore_name': chore.name,
                    'date': completion_date.strftime('%Y-%m-%d'),
                    'percentage': 1.0 - percentage,
                    'assigned_by': current_user.id
                })
            
            # Check for any pending assignments for this chore
            # 1. Check assignments where the current user is the assignee
            user_assignments = ChoreAssignment.query.filter_by(
                assignee_id=current_user.id,
                chore_id=form.chore_id.data,
                status='pending'
            ).all()
            
            # 2. If the chore was shared, also check assignments for the other user
            other_user_assignments = []
            if form.is_shared.data:
                other_user_assignments = ChoreAssignment.query.filter_by(
                    assignee_id=form.other_user_id.data,
                    chore_id=form.chore_id.data,
                    status='pending'
                ).all()
            
            # 3. Mark all found assignments as completed
            assignments_completed = 0
            for assignment in user_assignments + other_user_assignments:
                assignment.status = 'completed'
                assignments_completed += 1
            
            if assignments_completed > 0:
                db.session.commit()
                if assignments_completed == 1:
                    flash('A pending assignment for this chore has been automatically marked as completed!', 'success')
                else:
                    flash(f'{assignments_completed} pending assignments for this chore have been automatically marked as completed!', 'success')
            
            if completion_date == date.today():
                flash('Chore completed!', 'success')
            else:
                flash(f'Chore completed for {completion_date.strftime("%b %d, %Y")}!', 'success')
                
            return redirect(url_for(redirect_to))
        
        return redirect(url_for(redirect_to))
    
    @app.route('/assign_chore', methods=['GET', 'POST'])
    @login_required
    def assign_chore():
        if not current_user.home_id:
            flash('You need to be assigned to a home before you can assign chores.', 'warning')
            if current_user.is_admin:
                return redirect(url_for('admin_homes'))
            return render_template('no_home.html')
        
        form = ChoreAssignmentForm()
        
        # Populate dropdown choices
        chores = Chore.query.filter_by(home_id=current_user.home_id).all()
        form.chore_id.choices = [(c.id, c.name) for c in chores]
        
        users = User.query.filter_by(home_id=current_user.home_id).all()
        # Include current user in the assignee choices
        form.assignee_id.choices = [(u.id, u.username) for u in users]
        
        if form.validate_on_submit():
            # Check if the assignee has already completed this chore on the due date
            existing_completion = ChoreCompletion.query.filter_by(
                user_id=form.assignee_id.data,
                chore_id=form.chore_id.data,
                date=form.due_date.data
            ).first()
            
            if existing_completion:
                # Get user and chore names for the message
                assignee = User.query.get(form.assignee_id.data)
                chore = Chore.query.get(form.chore_id.data)
                
                # Different message if assigning to self or someone else
                if assignee.id == current_user.id:
                    flash(f'You have already completed "{chore.name}" on {form.due_date.data.strftime("%b %d, %Y")}. No need to create an assignment.', 'warning')
                else:
                    flash(f'{assignee.username} has already completed "{chore.name}" on {form.due_date.data.strftime("%b %d, %Y")}. No need to create an assignment.', 'warning')
                
                return redirect(url_for('assign_chore'))
            
            # Proceed with creating the assignment if not already completed
            assignment = ChoreAssignment(
                assigner_id=current_user.id,
                assignee_id=form.assignee_id.data,
                chore_id=form.chore_id.data,
                due_date=form.due_date.data,
                points=form.points.data,
                notes=form.notes.data
            )
            
            db.session.add(assignment)
            db.session.commit()
            
            # Get the chore and assignee details for the calendar event
            chore = Chore.query.get(form.chore_id.data)
            assignee = User.query.get(form.assignee_id.data)
            
            # Parse time if provided
            due_time = None
            if form.due_time.data:
                try:
                    hours, minutes = form.due_time.data.split(':')
                    due_time = time(int(hours), int(minutes))
                except (ValueError, AttributeError):
                    # Default to 10:00 AM if time parsing fails
                    due_time = time(10, 0)
            else:
                # Default to 10:00 AM if no time provided
                due_time = time(10, 0)
            
            # Create datetime by combining date and time with local timezone
            local_tz = pytz.timezone('America/New_York')  # Eastern Time Zone
            due_datetime = datetime.combine(form.due_date.data, due_time)
            due_datetime = local_tz.localize(due_datetime)
            
            # Check if calendar integration is requested and the assignee has connected their Google Calendar
            if form.add_to_calendar.data and assignee and UserCalendarToken.query.filter_by(user_id=assignee.id).first():
                # Add to their Google Calendar with the specific time
                success, message = add_calendar_event(
                    user_id=assignee.id,
                    chore_name=chore.name,
                    due_date=due_datetime,  # Pass the datetime object instead of just the date
                    notes=form.notes.data
                )
                
                if success:
                    if assignee.id == current_user.id:
                        flash(f'Chore assigned to yourself successfully and added to your Google Calendar!', 'success')
                    else:
                        flash(f'Chore assigned successfully and added to {assignee.username}\'s Google Calendar!', 'success')
                else:
                    flash(f'Chore assigned successfully, but failed to add to calendar: {message}', 'warning')
            else:
                if form.add_to_calendar.data and not UserCalendarToken.query.filter_by(user_id=assignee.id).first():
                    if assignee.id == current_user.id:
                        flash(f'Chore assigned to yourself successfully! Note: You have not connected your Google Calendar yet.', 'info')
                    else:
                        flash(f'Chore assigned successfully! Note: {assignee.username} has not connected their Google Calendar yet.', 'info')
                else:
                    if assignee.id == current_user.id:
                        flash('Chore assigned to yourself successfully!', 'success')
                    else:
                        flash('Chore assigned successfully!', 'success')
            
            # Redirect back to the assign_chore page instead of dashboard
            return redirect(url_for('assign_chore'))
        
        # Get users with their Google Calendar connection status for the template
        for user in users:
            user.has_calendar = UserCalendarToken.query.filter_by(user_id=user.id).first() is not None
        
        # Get today's date for checking existing completions/assignments
        today = date.today()
        
        # Get completions for today
        today_completions = ChoreCompletion.query.filter(
            ChoreCompletion.user_id.in_([u.id for u in users]),
            ChoreCompletion.date == today
        ).all()
        
        # Create a mapping of completed chores by user
        user_completed_chores = {}
        for completion in today_completions:
            if completion.user_id not in user_completed_chores:
                user_completed_chores[completion.user_id] = []
            user_completed_chores[completion.user_id].append(completion.chore_id)
        
        # Get existing assignments for today and future dates
        existing_assignments = ChoreAssignment.query.filter(
            ChoreAssignment.assignee_id.in_([u.id for u in users]),
            ChoreAssignment.due_date >= today,
            ChoreAssignment.status == 'pending'
        ).all()
        
        # Create a mapping of assigned chores by user and date
        user_assigned_chores = {}
        for assignment in existing_assignments:
            date_str = assignment.due_date.strftime('%Y-%m-%d')
            key = f"{assignment.assignee_id}_{date_str}"
            if key not in user_assigned_chores:
                user_assigned_chores[key] = []
            user_assigned_chores[key].append(assignment.chore_id)
        
        return render_template('assign_chore.html', form=form, users=users, 
                              today_completions=today_completions,
                              user_completed_chores=user_completed_chores,
                              existing_assignments=existing_assignments,
                              user_assigned_chores=user_assigned_chores,
                              chores=chores,
                              today=today)
    
    @app.route('/penalize_assignment/<int:assignment_id>', methods=['POST'])
    @login_required
    def penalize_assignment(assignment_id):
        assignment = ChoreAssignment.query.get_or_404(assignment_id)
        
        # Make sure user is the assigner and belongs to the same home
        if assignment.assigner_id != current_user.id:
            flash('You can only penalize assignments you created.', 'danger')
            return redirect(url_for('dashboard'))
        
        penalty = float(request.form.get('penalty_points', 0))
        if penalty <= 0:
            flash('Penalty must be a positive number.', 'warning')
            return redirect(url_for('dashboard'))
        
        assignment.status = 'missed'
        assignment.penalty_points = penalty
        db.session.commit()
        
        flash('Penalty has been applied.', 'success')
        return redirect(url_for('dashboard'))
    
    # ADMIN ROUTES
    @app.route('/admin/homes', methods=['GET', 'POST'])
    @login_required
    def admin_homes():
        if not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        
        form = HomeForm()
        homes = Home.query.all()
        
        if form.validate_on_submit():
            home = Home(name=form.name.data)
            db.session.add(home)
            db.session.commit()
            flash(f'Home "{form.name.data}" created!', 'success')
            return redirect(url_for('admin_homes'))
        
        return render_template('admin_homes.html', form=form, homes=homes)
    
    @app.route('/admin/edit_home/<int:home_id>', methods=['POST'])
    @login_required
    def edit_home(home_id):
        if not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        
        home = Home.query.get_or_404(home_id)
        new_name = request.form.get('name')
        
        if not new_name:
            flash('Home name cannot be empty.', 'danger')
            return redirect(url_for('admin_homes'))
        
        old_name = home.name
        home.name = new_name
        db.session.commit()
        
        flash(f'Home name updated from "{old_name}" to "{new_name}".', 'success')
        return redirect(url_for('admin_homes'))
    
    @app.route('/admin/delete_home/<int:home_id>', methods=['POST'])
    @login_required
    def delete_home(home_id):
        if not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        
        home = Home.query.get_or_404(home_id)
        
        # Check if home has any users
        if home.users:
            flash(f'Cannot delete "{home.name}" because it has users assigned to it. Reassign users first.', 'danger')
            return redirect(url_for('admin_homes'))
        
        # Store the name for the flash message
        home_name = home.name
        
        # Delete chores and related data
        chores = Chore.query.filter_by(home_id=home.id).all()
        for chore in chores:
            ChoreCompletion.query.filter_by(chore_id=chore.id).delete()
            ChoreAssignment.query.filter_by(chore_id=chore.id).delete()
            ChoreHistory.query.filter_by(chore_id=chore.id).delete()
            ChoreChallenge.query.filter_by(chore_id=chore.id).delete()
            db.session.delete(chore)
        
        # Delete the home
        db.session.delete(home)
        db.session.commit()
        
        flash(f'Home "{home_name}" has been deleted successfully.', 'success')
        return redirect(url_for('admin_homes'))
    
    @app.route('/admin/users', methods=['GET', 'POST'])
    @login_required
    def admin_users():
        if not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        
        form = UserForm()
        
        # Populate dropdown choices
        homes = Home.query.all()
        form.home_id.choices = [(h.id, h.name) for h in homes]
        form.home_id.choices.insert(0, (0, 'No Home (Admin Only)'))
        
        users = User.query.all()
        
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            
            if not user:
                flash(f'User {form.username.data} not found.', 'danger')
            else:
                if form.home_id.data == 0:
                    user.home_id = None
                else:
                    user.home_id = form.home_id.data
                
                user.is_admin = form.is_admin.data
                db.session.commit()
                flash(f'User {user.username} updated!', 'success')
            
            return redirect(url_for('admin_users'))
        
        return render_template('admin_users.html', form=form, users=users)
    
    @app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
    @login_required
    def delete_user(user_id):
        if not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        
        user = User.query.get_or_404(user_id)
        
        # Don't allow admin to delete themselves
        if user.id == current_user.id:
            flash('You cannot delete your own account.', 'danger')
            return redirect(url_for('admin_users'))
        
        # Store the username for the flash message
        username = user.username
        
        # Delete the user's related data
        ChoreCompletion.query.filter_by(user_id=user.id).delete()
        ChoreAssignment.query.filter_by(assignee_id=user.id).delete()
        ChoreAssignment.query.filter_by(assigner_id=user.id).delete()
        ChoreHistory.query.filter_by(creator_id=user.id).delete()
        ChoreChallenge.query.filter_by(challenger_id=user.id).delete()
        ChoreChallenge.query.filter_by(challenged_id=user.id).delete()
        
        # Delete calendar tokens if any
        UserCalendarToken.query.filter_by(user_id=user.id).delete()
        
        # Finally delete the user
        db.session.delete(user)
        db.session.commit()
        
        flash(f'User "{username}" has been deleted successfully.', 'success')
        return redirect(url_for('admin_users'))
    
    # API ENDPOINTS FOR AJAX CALLS
    @app.route('/api/user_stats')
    @login_required
    def api_user_stats():
        if not current_user.home_id:
            return jsonify({'error': 'No home assigned'}), 400
        
        # Get date ranges
        today = date.today()
        year = today.year  # Always use current year
        
        # Home users
        home_users = User.query.filter_by(home_id=current_user.home_id).all()
        user_ids = [u.id for u in home_users]
        usernames = {u.id: u.username for u in home_users}
        
        # Monthly data
        monthly_data = []
        
        for month in range(1, 13):
            start_date = date(year, month, 1)
            # Calculate end date (last day of month)
            if month == 12:
                end_date = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(year, month + 1, 1) - timedelta(days=1)
            
            # Skip future months
            if start_date > today:
                continue
            
            month_stats = {user_id: 0 for user_id in user_ids}
            
            # Get completions for this month
            completions = ChoreCompletion.query.join(Chore).filter(
                Chore.home_id == current_user.home_id,
                ChoreCompletion.date >= start_date,
                ChoreCompletion.date <= end_date,
                ChoreCompletion.user_id.in_(user_ids)
            ).all()
            
            # Calculate points per user
            for c in completions:
                month_stats[c.user_id] += c.percentage
            
            monthly_data.append({
                'month': month,
                'month_name': start_date.strftime('%B'),
                'user_points': month_stats
            })
        
        # Weekly data (last 10 weeks)
        weekly_data = []
        current_week_start = today - timedelta(days=today.weekday())
        
        for week_offset in range(9, -1, -1):
            week_start = current_week_start - timedelta(weeks=week_offset)
            week_end = week_start + timedelta(days=6)
            
            # Skip future weeks
            if week_start > today:
                continue
            
            week_stats = {user_id: 0 for user_id in user_ids}
            
            # Get completions for this week
            completions = ChoreCompletion.query.join(Chore).filter(
                Chore.home_id == current_user.home_id,
                ChoreCompletion.date >= week_start,
                ChoreCompletion.date <= week_end,
                ChoreCompletion.user_id.in_(user_ids)
            ).all()
            
            # Calculate points per user
            for c in completions:
                week_stats[c.user_id] += c.percentage
            
            weekly_data.append({
                'week_start': week_start.strftime('%Y-%m-%d'),
                'week_label': f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}",
                'user_points': week_stats
            })
        
        return jsonify({
            'users': usernames,
            'weekly_data': weekly_data,
            'monthly_data': monthly_data
        })
    
    @app.route('/api/chore_stats')
    @login_required
    def api_chore_stats():
        if not current_user.home_id:
            return jsonify({'error': 'No home assigned'}), 400
        
        # Get chores for this home
        chores = Chore.query.filter_by(home_id=current_user.home_id).all()
        chore_names = {c.id: c.name for c in chores}
        
        # Home users
        home_users = User.query.filter_by(home_id=current_user.home_id).all()
        usernames = {u.id: u.username for u in home_users}
        
        # Get overall chore completions per user per chore
        chore_stats = []
        
        for chore in chores:
            # Get completions by user for this chore
            user_completions = db.session.query(
                ChoreCompletion.user_id,
                func.count(ChoreCompletion.id).label('count'),
                func.sum(ChoreCompletion.percentage).label('total_percentage')
            ).filter(
                ChoreCompletion.chore_id == chore.id
            ).group_by(ChoreCompletion.user_id).all()
            
            user_stats = {}
            for user_id, count, total in user_completions:
                if user_id in usernames:
                    user_stats[user_id] = {
                        'count': count,
                        'total_points': float(total),
                        'username': usernames.get(user_id, 'Unknown')
                    }
            
            chore_stats.append({
                'chore_id': chore.id,
                'chore_name': chore.name,
                'user_stats': user_stats
            })
        
        return jsonify({
            'chores': chore_names,
            'users': usernames,
            'chore_stats': chore_stats
        })
    
    @app.route('/approve_challenge/<int:challenge_id>/<action>', methods=['POST'])
    @login_required
    def approve_challenge(challenge_id, action):
        if action not in ['approve', 'reject']:
            flash('Invalid action.', 'danger')
            return redirect(url_for('chore_history'))
        
        # Get the challenge
        challenge = ChoreChallenge.query.get_or_404(challenge_id)
        
        # Check if the user is the challenger
        if challenge.challenger_id != current_user.id:
            flash('You can only approve or reject challenges you initiated.', 'danger')
            return redirect(url_for('chore_history'))
        
        # Check if the challenge is in pending_approval state
        if challenge.status != 'pending_approval':
            flash('This challenge is not awaiting approval.', 'warning')
            return redirect(url_for('chore_history'))
        
        # Get the completion
        completion = ChoreCompletion.query.get(challenge.completion_id)
        
        # Get the chore for notifications
        chore = Chore.query.get(completion.chore_id)
        
        if action == 'approve':
            # Update challenge
            challenge.status = 'accepted'
            challenge.resolution_date = datetime.now()
            
            # Get the original percentage before adjustment
            original_percentage = completion.percentage
            
            # Update completion with the adjusted percentage
            completion.percentage = challenge.adjustment_percentage
            completion.status = 'adjusted'
            
            # Find other completions for the same chore on the same date by other users (shared completions)
            other_completions = ChoreCompletion.query.filter(
                ChoreCompletion.chore_id == completion.chore_id,
                ChoreCompletion.date == completion.date,
                ChoreCompletion.id != completion.id
            ).all()
            
            if other_completions:
                # If there are other completions (shared chore), adjust their percentages fairly
                
                # For simplicity, handle the common case of just one other user 
                if len(other_completions) == 1:
                    other_completion = other_completions[0]
                    # The other user gets the remaining percentage (ensuring total is 100%)
                    new_percentage = 1.0 - challenge.adjustment_percentage
                    
                    # Apply the new percentage
                    other_completion.percentage = new_percentage
                    other_completion.status = 'adjusted'
                    
                    # Create a notification for the user whose percentage was adjusted
                    notification = f"Your percentage for '{chore.name}' on {completion.date.strftime('%b %d, %Y')} was adjusted from {int(other_completion.percentage * 100)}% to {int(new_percentage * 100)}% due to a challenge resolution. User {User.query.get(completion.user_id).username}'s percentage was adjusted to {int(challenge.adjustment_percentage * 100)}%."
                    
                    # We would ideally store this notification in a database table
                    # For now, we'll add a flash message that will show on next login
                    flash(notification, 'info')
                    
                    app.logger.info(f"Adjusted user {other_completion.user_id}'s percentage for chore {completion.chore_id} from {other_completion.percentage} to {new_percentage}")
                else:
                    # Handle the case of multiple other users
                    # Calculate how much percentage is available to distribute among other users
                    remaining_percentage = 1.0 - challenge.adjustment_percentage
                    
                    # Calculate the sum of original percentages of other users
                    original_others_total = sum(oc.percentage for oc in other_completions)
                    
                    # Prepare a summary notification about the overall adjustment
                    adjustment_summary = f"A challenge for '{chore.name}' on {completion.date.strftime('%b %d, %Y')} was resolved. User {User.query.get(completion.user_id).username}'s percentage was adjusted to {int(challenge.adjustment_percentage * 100)}%."
                    
                    # Distribute the remaining percentage proportionally based on original distribution
                    for other_completion in other_completions:
                        # Store original percentage for notification
                        original_user_percentage = other_completion.percentage
                        
                        if original_others_total > 0:
                            # Calculate what proportion of the original percentage this user had
                            original_proportion = other_completion.percentage / original_others_total
                            
                            # Apply that same proportion to the remaining percentage
                            new_percentage = remaining_percentage * original_proportion
                        else:
                            # If all were 0 (unusual case), distribute equally
                            new_percentage = remaining_percentage / len(other_completions)
                        
                        # Apply the new percentage, ensuring it's within reasonable bounds
                        new_percentage = max(0.01, min(0.99, new_percentage))
                        other_completion.percentage = new_percentage
                        other_completion.status = 'adjusted'
                        
                        # Create a detailed notification for each user
                        user_notification = f"Your percentage for '{chore.name}' on {completion.date.strftime('%b %d, %Y')} was adjusted from {int(original_user_percentage * 100)}% to {int(new_percentage * 100)}% as part of an overall rebalancing. {adjustment_summary}"
                        
                        # We would ideally store this notification in a database table
                        # For now, we'll add a flash message that will show on next login
                        flash(user_notification, 'info')
                        
                        app.logger.info(f"Adjusted user {other_completion.user_id}'s percentage for chore {completion.chore_id} from {original_user_percentage} to {new_percentage}")
                    
                    # Verify the total is approximately 100% (allowing for floating point errors)
                    total_percentage = challenge.adjustment_percentage + sum(oc.percentage for oc in other_completions)
                    if abs(total_percentage - 1.0) > 0.001:
                        app.logger.warning(f"Total percentage after adjustment is {total_percentage}, not 1.0 as expected")
            
            flash('You have approved the adjustment. Percentages for all involved users have been updated.', 'success')
        else:  # reject
            # Reset the challenge to pending so the user can respond again
            challenge.status = 'pending'
            challenge.defense_comment = None
            challenge.adjustment_percentage = None
            
            flash('You have rejected the proposed adjustment. The challenged user can respond again.', 'info')
        
        db.session.commit()
        return redirect(url_for('chore_history'))
    
    # Google Calendar OAuth Routes
    @app.route('/calendar/connect')
    @login_required
    def connect_calendar():
        # Generate authorization URL
        auth_url, state = get_authorization_url()
        
        # Store state in session for verification
        session['google_auth_state'] = state
        
        # Redirect user to Google's OAuth consent screen
        return redirect(auth_url)
    
    @app.route('/calendar/oauth2callback')
    @login_required
    def calendar_oauth_callback():
        # Get authorization code
        code = request.args.get('code')
        state = request.args.get('state')
        
        # Verify state to prevent CSRF
        if state != session.get('google_auth_state'):
            flash('Invalid authentication state.', 'danger')
            return redirect(url_for('dashboard'))
        
        try:
            # Process callback and get tokens
            access_token, refresh_token, expiry = process_oauth_callback(code)
            
            # Save tokens to database
            save_tokens(current_user.id, access_token, refresh_token, expiry)
            
            flash('Google Calendar connected successfully!', 'success')
        except Exception as e:
            flash(f'Failed to connect Google Calendar: {str(e)}', 'danger')
        
        return redirect(url_for('dashboard'))
    
    @app.route('/calendar/disconnect')
    @login_required
    def disconnect_calendar():
        # Remove the user's calendar token
        token = UserCalendarToken.query.filter_by(user_id=current_user.id).first()
        if token:
            db.session.delete(token)
            db.session.commit()
            flash('Google Calendar disconnected successfully.', 'success')
        else:
            flash('No Google Calendar connection found.', 'warning')
        
        return redirect(url_for('dashboard'))
    
    @app.route('/export/<period>')
    @login_required
    def export_data(period):
        """
        Generate Excel file with chore data for the specified period.
        Period can be: 'weekly', 'monthly', or 'ytd' (year to date)
        """
        today = datetime.now().date()
        
        # Define the start date based on the period
        if period == 'weekly':
            start_date = today - timedelta(days=7)
            title = f"Weekly Chore Summary ({start_date.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')})"
        elif period == 'monthly':
            start_date = today.replace(day=1)
            title = f"Monthly Chore Summary ({start_date.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')})"
        elif period == 'ytd':
            start_date = today.replace(month=1, day=1)
            title = f"Year-to-Date Chore Summary ({start_date.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')})"
        else:
            flash('Invalid period specified', 'danger')
            return redirect(url_for('dashboard'))
        
        # Create in-memory output file
        output = io.BytesIO()
        
        # Create workbook and worksheet
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Chore Summary')
        
        # Add formatting
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#4F81BD',
            'font_color': 'white'
        })
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D0D7E5',
            'border': 1
        })
        
        cell_format = workbook.add_format({
            'border': 1
        })
        
        date_format = workbook.add_format({
            'border': 1,
            'num_format': 'yyyy-mm-dd'
        })
        
        percent_format = workbook.add_format({
            'border': 1,
            'num_format': '0%'
        })
        
        # Write title
        worksheet.merge_range('A1:F1', title, title_format)
        worksheet.set_row(0, 30)
        
        # Write headers
        headers = ['Date', 'Chore', 'User', 'Percentage', 'Status', 'Points']
        for col, header in enumerate(headers):
            worksheet.write(1, col, header, header_format)
        
        # Set column widths
        worksheet.set_column('A:A', 12)
        worksheet.set_column('B:B', 25)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 12)
        worksheet.set_column('E:E', 15)
        worksheet.set_column('F:F', 10)
        
        # Get home users for summary
        home = Home.query.get(current_user.home_id)
        home_users = User.query.filter_by(home_id=home.id).all()
        user_names = {user.id: user.username for user in home_users}
        
        # Get completions for this period
        completions = ChoreCompletion.query.join(Chore).filter(
            ChoreCompletion.user_id.in_([user.id for user in home_users]),
            ChoreCompletion.date >= start_date,
            ChoreCompletion.date <= today,
            Chore.home_id == home.id
        ).order_by(ChoreCompletion.date.desc()).all()
        
        # Write data
        row = 2
        for completion in completions:
            chore = Chore.query.get(completion.chore_id)
            worksheet.write_datetime(row, 0, datetime.combine(completion.date, datetime.min.time()), date_format)
            worksheet.write(row, 1, chore.name, cell_format)
            worksheet.write(row, 2, user_names.get(completion.user_id, "Unknown"), cell_format)
            worksheet.write_number(row, 3, completion.percentage, percent_format)
            worksheet.write(row, 4, completion.status.capitalize(), cell_format)
            worksheet.write_number(row, 5, completion.percentage, cell_format)  # Points = percentage
            row += 1
        
        # Add summary section
        summary_row = row + 2
        worksheet.merge_range(f'A{summary_row}:F{summary_row}', 'Summary by User', title_format)
        
        # Write summary headers
        summary_headers = ['User', 'Chores Completed', 'Total Points', 'Percentage of Total']
        for col, header in enumerate(summary_headers):
            worksheet.write(summary_row + 1, col, header, header_format)
        
        # Calculate summary data
        user_stats = {}
        total_points = 0
        
        for completion in completions:
            user_id = completion.user_id
            if user_id not in user_stats:
                user_stats[user_id] = {'count': 0, 'points': 0}
            
            user_stats[user_id]['count'] += 1
            user_stats[user_id]['points'] += completion.percentage
            total_points += completion.percentage
        
        # Write summary data
        summary_row += 2
        for user_id, stats in user_stats.items():
            worksheet.write(summary_row, 0, user_names.get(user_id, "Unknown"), cell_format)
            worksheet.write(summary_row, 1, stats['count'], cell_format)
            worksheet.write(summary_row, 2, stats['points'], cell_format)
            
            if total_points > 0:
                percentage = stats['points'] / total_points
            else:
                percentage = 0
            
            worksheet.write(summary_row, 3, percentage, percent_format)
            summary_row += 1
        
        # Close the workbook
        workbook.close()
        
        # Prepare the output
        output.seek(0)
        
        # Send the file
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f"chore_summary_{period}_{today.strftime('%Y%m%d')}.xlsx"
        )
    
    @app.route('/admin/usage_stats')
    @login_required
    def admin_usage_stats():
        if not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        
        # Get basic stats
        total_users = User.query.count()
        total_homes = Home.query.count()
        total_chores = Chore.query.count()
        total_completions = ChoreCompletion.query.count()
        
        # User activity stats
        today = datetime.now().date()
        start_of_today = datetime.combine(today, datetime.min.time())
        
        # Daily active users (unique users with activity today)
        daily_active_users = db.session.query(UserActivity.user_id).distinct().filter(
            UserActivity.timestamp >= start_of_today
        ).count()
        
        # Weekly active users
        week_ago = today - timedelta(days=7)
        start_of_week = datetime.combine(week_ago, datetime.min.time())
        weekly_active_users = db.session.query(UserActivity.user_id).distinct().filter(
            UserActivity.timestamp >= start_of_week
        ).count()
        
        # Monthly active users
        month_ago = today - timedelta(days=30)
        start_of_month = datetime.combine(month_ago, datetime.min.time())
        monthly_active_users = db.session.query(UserActivity.user_id).distinct().filter(
            UserActivity.timestamp >= start_of_month
        ).count()
        
        # Get activity counts by action type
        action_stats = db.session.query(
            UserActivity.action, 
            func.count(UserActivity.id)
        ).group_by(UserActivity.action).all()
        
        action_counts = {action: count for action, count in action_stats}
        
        # Get activity counts by day for the past 30 days
        daily_activity = []
        for day_offset in range(30, -1, -1):
            day_date = today - timedelta(days=day_offset)
            start_of_day = datetime.combine(day_date, datetime.min.time())
            end_of_day = datetime.combine(day_date, datetime.max.time())
            
            day_count = UserActivity.query.filter(
                UserActivity.timestamp >= start_of_day,
                UserActivity.timestamp <= end_of_day
            ).count()
            
            unique_users = db.session.query(UserActivity.user_id).distinct().filter(
                UserActivity.timestamp >= start_of_day,
                UserActivity.timestamp <= end_of_day
            ).count()
            
            daily_activity.append({
                'date': day_date.strftime('%Y-%m-%d'),
                'day': day_date.strftime('%b %d'),
                'activity_count': day_count,
                'unique_users': unique_users
            })
        
        # Get top users by activity
        top_users = db.session.query(
            UserActivity.user_id,
            func.count(UserActivity.id).label('activity_count')
        ).group_by(UserActivity.user_id).order_by(func.count(UserActivity.id).desc()).limit(10).all()
        
        top_users_data = []
        for user_id, count in top_users:
            user = User.query.get(user_id)
            if user:
                user_completions = ChoreCompletion.query.filter_by(user_id=user_id).count()
                top_users_data.append({
                    'user_id': user_id,
                    'username': user.username,
                    'activity_count': count,
                    'completions': user_completions,
                    'home': Home.query.get(user.home_id).name if user.home_id else 'No Home'
                })
        
        # Return all stats
        return render_template('admin_usage_stats.html',
                              total_users=total_users,
                              total_homes=total_homes,
                              total_chores=total_chores,
                              total_completions=total_completions,
                              daily_active_users=daily_active_users,
                              weekly_active_users=weekly_active_users,
                              monthly_active_users=monthly_active_users,
                              action_counts=action_counts,
                              daily_activity=daily_activity,
                              top_users=top_users_data)
    
    @app.route('/delete_chore_completion', methods=['POST'])
    @login_required
    def delete_chore_completion():
        if not current_user.home_id:
            flash('You need to be assigned to a home before you can manage completions.', 'warning')
            return redirect(url_for('dashboard'))
        
        completion_id = request.form.get('completion_id')
        if not completion_id:
            flash('Invalid request. No completion specified.', 'danger')
            return redirect(url_for('chore_history'))
        
        # Get the completion
        completion = ChoreCompletion.query.get_or_404(completion_id)
        
        # Security checks
        # 1. Ensure user can only delete their own completions
        if completion.user_id != current_user.id:
            flash('You can only delete your own chore completions.', 'danger')
            return redirect(url_for('chore_history'))
        
        # 2. Ensure the chore is from the user's home
        chore = Chore.query.get(completion.chore_id)
        if not chore or chore.home_id != current_user.home_id:
            flash('You can only delete completions for chores in your own home.', 'danger')
            return redirect(url_for('chore_history'))
        
        # 3. Only active completions can be deleted (not challenged or adjusted)
        if completion.status != 'active':
            flash('You cannot delete completions that have been challenged or adjusted.', 'danger')
            return redirect(url_for('chore_history'))
        
        # Get completion details for tracking
        chore_name = chore.name
        completion_date = completion.date
        completion_percentage = completion.percentage
        
        # Check if this completion has any challenges
        if completion.challenges:
            # Delete all challenges for this completion
            for challenge in completion.challenges:
                db.session.delete(challenge)
        
        # Check if this is part of a shared chore with other users
        other_completions = ChoreCompletion.query.filter(
            ChoreCompletion.chore_id == completion.chore_id,
            ChoreCompletion.date == completion.date,
            ChoreCompletion.id != completion.id
        ).all()
        
        # Delete the completion
        db.session.delete(completion)
        
        # Track activity
        track_activity(current_user.id, 'delete_chore_completion', 'chore_history', {
            'chore_id': chore.id,
            'chore_name': chore_name,
            'date': completion_date.strftime('%Y-%m-%d'),
            'percentage': completion_percentage
        })
        
        db.session.commit()
        
        # Check for any completed assignments that need to be reopened
        # Only assignments where the current user was the assignee
        assignments = ChoreAssignment.query.filter_by(
            assignee_id=current_user.id,
            chore_id=chore.id,
            status='completed',
            due_date=completion_date
        ).all()
        
        if assignments:
            for assignment in assignments:
                assignment.status = 'pending'
            db.session.commit()
            if len(assignments) == 1:
                flash('A previously completed assignment has been reopened.', 'info')
            else:
                flash(f'{len(assignments)} previously completed assignments have been reopened.', 'info')
        
        flash(f'Chore completion for "{chore_name}" on {completion_date.strftime("%b %d, %Y")} has been deleted.', 'success')
        return redirect(url_for('chore_history')) 