# Household Chore Tracker - Project Context

## Overview

This is a beautifully designed, responsive web application for tracking daily household chores among multiple households. The system provides transparency, fair distribution of responsibilities, and an engaging, gamified experience — all wrapped in a modern and visually attractive UI.

## Objective

- Provide an intuitive and modern way to manage daily household chores.
- Enable **multi-tenant usage** with support for multiple households.
- Allow users to track their individual and shared contributions.
- Visualize activity and fairness metrics in an engaging dashboard.
- Make chore logging fun and rewarding through gamification and design.
- Maintain simple user management with admin control.
- Enable chore assignment and accountability between users.

---

## Key Features

### 1. **User Authentication, Roles, and Multi-Tenant Support**
- Secure login system with username and password.
- The **first registered user becomes the global admin**.
- Admin privileges include:
  - Adding and removing households ("homes")
  - Adding users to specific households
  - Managing household-level data
- Each **household (home)** has:
  - Its own set of users
  - Its own chore list
  - Its own chore completion and assignment records
  - An isolated dashboard
- Regular users can:
  - Log chores
  - Add new chores (home-specific)
  - Share chores with other users in the same home
  - View dashboards scoped to their household
  - Assign chores within their home

---

### 2. **Chore Selection and Completion**
- Users see a **modern checklist interface** with chore names and toggle switches.
- Includes a **search bar** to filter chores easily with real-time results.
- Users can select **multiple chores** and log them all at once.
- If a chore is missing, any user can add it on the fly.
- All chores carry a **uniform point value** (e.g., 1 point).
- Users can **backdate chore completions** for logging tasks completed on previous days.

---

### 3. **Chore Sharing & Partial Completion**
- Users can choose to:
  - ✅ Mark a chore as **fully completed** (100%)
  - 🔄 **Split the chore** with the other user
- When splitting:
  - The logged-in user enters the **percentage they completed** (e.g., 40%)
  - Selects the **other user from a dropdown**
  - The system automatically assigns the remaining percentage to the other user (e.g., 60%)
  - Two completion records are created and points are distributed accordingly
- **Fair Point Distribution**: When chore percentages are adjusted through challenges, all users sharing the chore have their percentages updated proportionally to maintain fairness.

---

### 4. **Daily Tracking**
- Prevents duplicate chore entries for the same user on the same day.
- Stores full chore completion history, including:
  - Chore name
  - Date
  - Percentage completed
  - Who completed it

---

### 5. **Chore Challenge System**
- Users can challenge a chore completion if they disagree with the percentage allocation.
- The challenged user can defend by proposing an adjusted percentage.
- Original challenger can approve or reject the defense.
- Notifications inform users when their chore percentages are adjusted.
- Admin oversight ensures fair resolution of challenges.

---

### 6. **Dashboard (Modern & Visual)**
An engaging and creative dashboard shows real-time and historical analytics with beautiful visual components.

#### Features:
- ✅ **Total Chores Completed**
  - Per user, cumulative count
  - Filterable by user selection

- 🏆 **Points Earned**
  - Calculated based on percentages (e.g., 0.4, 1.0)
  - Individual and combined views

- 📊 **Trends (Weekly/Monthly/Yearly)**
  - Line/area/bar charts to show activity over time
  - User comparison charts
  - Monthly points distribution
  - Year selection (2025-2035)

- 👥 **Chore Dominance**
  - Highlights which user typically completes each chore
  - Shows completion count and total percentage
  - Example: "Vacuuming: Mostly done by User A (12 times, 80%)"

- 🏅 **Statistics**
  - Weekly completion rates
  - Monthly completion trends
  - Cumulative overview with trends
  - Individual user statistics

- 📅 **Today's Chores Summary**
  - What was completed today and by whom
  - Assigned chores status

#### Visual Style:
- **Responsive UI with animations** for transitions and feedback
- **Gradient backgrounds** and cards for dashboard tiles
- **Modern charting library** (Chart.js with gradients)
- **Custom icons or emojis** for chore types
- Built for both desktop and mobile

---

### 7. **Chore Assignment System**
- Users can assign chores to other users for specific dates
- Assignment features include:
  - Date selection for the task
  - User selection for assignment
  - Optional notes or instructions
  - Point value specification
- Assigned chores appear on the assignee's dashboard
- Completion tracking:
  - Assignee can mark assigned chores as complete
  - System tracks completion status and deadlines
- Penalty system:
  - Assigner can penalize incomplete assigned tasks
  - Points deduction from user's overall score
  - Penalty history tracking
- Notifications:
  - Users see assigned tasks upon login
  - Visual indicators for pending assignments
  - Deadline reminders

---

### 8. **Notification System**
- Users receive notifications for:
  - Chore challenges and defenses
  - Percentage adjustments to shared chores
  - Assignments and updates to assigned chores
  - Admin actions affecting their account or chores
- Notification history viewable within the application
- Flash messages for immediate feedback on actions

---

### 9. **Data Export System**
- Users can export chore data in Excel format for their household
- Export options include:
  - Weekly summary (last 7 days)
  - Monthly summary (current month)
  - Year-to-date summary
- Export files include:
  - Detailed list of all chore completions with dates, users, and percentages
  - Summary statistics by user (chores completed, points earned)
  - Visual formatting for easy readability
- Files are generated on-demand and automatically named with the period and date

---

### 10. **Google Calendar Integration** *(Phase 2 Implementation)*
- Assigned chores will automatically sync to the assignee's Google Calendar.
- Features:
  - OAuth-based integration to connect Google accounts
  - Tasks appear as calendar events with notes and deadlines
  - Option to include reminders/notifications via Google Calendar
  - Status updates in the app reflect on the calendar (e.g., completed, pending)
  - Admin can view synced tasks for all users in their household
  - Supports revoking access and re-authentication

---

## UI/UX Design Goals
- Sleek and **mobile-responsive layout** using **Bootstrap 5**
- Custom CSS with **modern animations**, hover effects, and transitions
- Use of **soft gradients**, **rounded cards**, and **elegant typography**
- Intuitive navigation with collapsible sidebars or navbar
- Smooth UX for chore selection, logging, and dashboard viewing
- Real-time search filtering for quick chore location
- Interactive feedback for user actions

---

## Tech Stack

### Frontend
- **HTML5**
- **CSS3** (with gradient styling and transitions)
- **Bootstrap 5**
- **Chart.js** for responsive, animated charts
- **JavaScript** for dynamic UI interactions

### Backend
- **Python (Flask)**
  - Flask Blueprints for modular structure
  - Flask-Login for secure authentication
  - Flask-WTF for form handling

### Database
- **PostgreSQL**
  - Robust and scalable for production use
  - Supports multiple concurrent users, ACID compliance, and advanced querying
  - Ideal for multi-tenant household tracking with strong relational integrity

### APIs
- **Google Calendar API** for task sync via OAuth2

---

## Database Schema

### Table: `homes` *(New)*
| id | name        |
|----|-------------|

### Table: `users`
| id | username | password_hash | is_admin | home_id |
|----|----------|----------------|----------|---------|

### Table: `chores`
| id | name     | home_id |
|----|----------|---------|

### Table: `chore_completions`
| id | user_id | chore_id | date       | percentage |
|----|---------|----------|------------|------------|

### Table: `chore_assignments`
| id | assigner_id | assignee_id | chore_id | due_date | points | notes | status | penalty_points |
|----|-------------|-------------|----------|----------|--------|-------|--------|----------------|

### Table: `user_calendar_tokens` *(New - for OAuth)*
| id | user_id | access_token | refresh_token | token_expiry |
|----|---------|---------------|----------------|----------------|

---

## Use Case Flow

1. First user registers → becomes global admin.
2. Admin creates a household and adds users to it.
3. Each user logs in and interacts only with their home's data.
4. Users log chores, share them, assign tasks, and view dashboards — all scoped to their home.
5. Assigned chores optionally sync to the user's Google Calendar if integrated.
6. The dashboard dynamically updates with all metrics.

---

## Future Enhancements

- **Reminder notifications via email/SMS**
- **PDF/CSV export of weekly/monthly summaries**
- **Dark mode**
- **Calendar integration** (Google — *Phase 2 implemented*)
- Apple/iCloud calendar integration (future)
- Optional task comments or notes
- Mobile app version
- Advanced analytics and reporting
- Customizable point system
- Multiple household support *(Implemented in Phase 1)*

---

## Project Goal

To create a **stylish, intuitive, and fair household chore tracking system** that not only manages responsibilities but makes the process engaging and even fun — with **smart visuals**, **interactive features**, and a **dashboard that feels like a productivity app, not a to-do list**. With **multi-tenant architecture** and **Google Calendar integration**, the system scales across households while enhancing personal accountability. It needs a modren design. The web page must be responsive on all the devices (Phones, Tablets and Webbowrser). A modren look and feel for all the pages. All the text must be readable (So black or contrasting colour for the texts with the background).
