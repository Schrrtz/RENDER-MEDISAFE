# MEDISAFE-PBL - Healthcare Management System

A Django-based healthcare management system with user and admin interfaces.

## Features

### User Interface
- **Homepage**: Landing page with login options
- **Dashboard**: Main user interface with navigation
- **Vitals**: Patient vital signs monitoring
- **Lab Results**: Laboratory test results with filtering
- **Alerts**: Notification and feedback system
- **User Profile**: Patient profile management

### Admin Interface
- **Admin Dashboard**: Comprehensive admin panel
- **Analytics**: Data visualization and KPIs
- **Patient Management**: Patient list and profiles
- **User Management**: Staff account management

## Getting Started

### Prerequisites
- Python 3.8+
- Django 5.2.6

### Installation

1. Navigate to the project directory:
```bash
cd PBL
```

2. Install Django (if not already installed):
```bash
pip install django
```

3. Run migrations:
```bash
python manage.py migrate
```

4. Start the development server:
```bash
python manage.py runserver
```

5. Open your browser and go to: `http://127.0.0.1:8000/`

## Usage

### User Login
1. Go to the homepage
2. Click the "Login" button to open the login modal
3. Enter credentials to access the system

### Login Options
- **Admin Access**: 
  - Username: `MEDISAFE`
  - Password: `CHOWKING`
  - Grants access to Admin Dashboard, Analytics, and Account Management
- **Client Access**: 
  - Any username and password combination
  - Grants access to regular user dashboard and features

### Navigation Flow

#### Login Flow:
```
Homepage → Login Modal → [Admin Dashboard OR User Dashboard]
  ├── Admin: Admin Dashboard → [Analytics, Accounts, Patient Management, User Management]
  └── Client: User Dashboard → [Vitals, Lab Results, Alerts, Profile]
```

## Project Structure

```
PBL/
├── MEDISAFE-PBL/          # Django project settings
│   ├── settings.py        # Project configuration
│   ├── urls.py           # Main URL routing
│   └── ...
├── myapp/                 # Main application
│   ├── views.py          # View functions
│   ├── urls.py           # App URL routing
│   ├── models.py         # Database models (empty)
│   └── templates/        # HTML templates
│       ├── homepage2.html
│       ├── DASHBOARD.html
│       ├── AdminDashboard.html
│       ├── vitals.html
│       ├── lab_results.html
│       ├── alertNotification_Comments.html
│       ├── user profile.html
│       └── analytics.html
├── db.sqlite3            # SQLite database
└── manage.py             # Django management script
```

## Security Features

- Session-based authentication
- Admin access control with secret code
- CSRF protection on forms
- Access restrictions for admin-only pages

## Next Steps for Development

1. **Database Models**: Create models for Patient, User, Vitals, LabResults
2. **Authentication**: Implement Django's built-in user authentication
3. **Data Persistence**: Connect frontend to database
4. **API Endpoints**: Create REST API for data operations
5. **Form Validation**: Add proper form handling and validation
6. **Security**: Implement proper password hashing and user management

## Admin Credentials

The admin credentials are currently hardcoded in `myapp/views.py`:
- Username: `MEDISAFE`
- Password: `CHOWKING`

For production, these should be moved to environment variables or a more secure authentication system.

## Support

For issues or questions, please check the Django documentation or create an issue in the project repository.
