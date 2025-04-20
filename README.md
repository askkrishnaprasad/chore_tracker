# Chore Tracker

A web application for tracking and managing household chores with points, challenges, and user management.

## Features

- User registration and authentication
- Chore creation and assignment
- Points system for completed chores
- Challenge system for dispute resolution
- Admin dashboard for system management
- User activity tracking
- Google Calendar integration

## Technology Stack

- **Backend**: Python, Flask
- **Database**: SQLite (development), PostgreSQL (production)
- **Frontend**: HTML, CSS, JavaScript
- **Authentication**: Flask-Login

## Installation

### Development Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/chore-tracker.git
   cd chore-tracker
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a `.env` file in the root directory with the following content:
   ```
   SECRET_KEY=your-secret-key-here
   DATABASE_URL=sqlite:///chore_tracker.db
   ```

5. Initialize the database:
   ```
   python init_db.py
   ```

6. Run the application:
   ```
   python run.py
   ```

7. Access the application at http://localhost:5001

### Production Deployment

See the [DEPLOY_RASPBERRY_PI.md](DEPLOY_RASPBERRY_PI.md) file for detailed instructions on deploying to a Raspberry Pi with PostgreSQL.

## Usage

1. Register for an account
2. Log in to the application
3. Create and assign chores
4. Complete chores to earn points
5. Challenge other users' chores if needed
6. Administrators can manage users and system settings

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/awesome-feature`)
3. Commit your changes (`git commit -m 'Add awesome feature'`)
4. Push to the branch (`git push origin feature/awesome-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 