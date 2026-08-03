# ABA Services Web Application

The ABA Services Web Application is a full-featured operations platform for ABA providers to manage clients, employees, sessions, invoices, payroll, mileage, reporting, and communications from a single system.

## Overview

This application supports the day-to-day operations of an ABA business with workflow tools for:

- client onboarding and parent/guardian management
- employee onboarding and role-based access
- session scheduling and documentation
- invoice generation and payment tracking
- payroll paystub creation
- mileage tracking
- reporting and administrative configuration

## Core Features

### User Authentication and Access Control

- Secure login and logout flow
- User registration with activation support
- Password reset flow
- Optional two-factor authentication (TOTP)
- Role-based access control for super users, admins, therapists, and supervisors

### Employee Management

- Add, edit, activate, and deactivate employees
- Assign roles, designations, and compensation rates
- Manage supervisor relationships and staffing assignments
- View active and inactive employees separately

### Client Management

- Onboard new clients with demographic and contact details
- Maintain parent/guardian contact information
- Assign supervisors and therapy/supervision rates
- Activate and deactivate clients safely
- Prevent client deactivation when dependencies such as unpaid invoices exist

### Intervention and Session Management

- Record therapy and supervision sessions
- Schedule sessions in the future
- Attach supporting files and notes to sessions
- View sessions in calendar and list views
- Bulk upload, bulk delete, and session filtering options
- Assign sessions to specific employees based on role and supervision structure

### Invoicing and Payments

- Generate invoices from completed sessions
- Preview invoices before finalizing them
- Track invoice lifecycle with Draft, Sent, and Paid status
- Support partial payments and payment history
- Update invoice balances automatically after payments
- Send invoice reminders based on due date and outstanding balance
- Email invoice PDFs to clients and support ad-hoc invoice email delivery
- Safe testing mode to prevent real outbound mail during development or testing

### Payroll and Paystubs

- Generate paystubs from sessions and configured pay rates
- Export paystubs as PDF
- Send paystubs to employees automatically or on demand
- Manage pay rates and payroll-related configuration

### Mileage Tracking

- Record mileage entries linked to business activities
- Manage mileage records through the web interface

### Reporting and Dashboard

- View dashboard statistics for sessions, invoicing, and payroll
- Review monthly trends for invoices and paystub totals
- Access reporting screens for operational insight

### Organization and Admin Settings

- Manage organization branding and contact details
- Configure Gmail OAuth email delivery
- Control reminder settings and testing email behavior
- Manage user accounts and system settings from the admin area

## Technology Stack

- Flask for the web application
- Flask-SQLAlchemy for data models and database access
- Flask-Migrate for database migrations
- Flask-Login for authentication
- WTForms for form handling
- Jinja2 templates for the UI
- PostgreSQL or SQLite for persistence
- Docker Compose for container-based deployment

## Deployment Options

### Docker Compose

The project includes a Docker Compose setup for running the application and its database together.

1. Copy the repository contents to your server or local environment.
2. Create a .env file with the required environment variables.
3. Start the stack with:

```bash
docker compose up -d
```

4. Open the app in your browser at the configured host port.

### Local Development

You can also run the app locally using the Python environment in the repository.

```bash
python -m pip install -r requirements.txt
python app.py
```

## Environment Variables

The application uses environment variables for organization information, database settings, and email safety.

Example:

```env
ORG_NAME="Your Organization"
ORG_ADDRESS="123 Main St"
ORG_PHONE="555-123-4567"
ORG_EMAIL="info@yourorg.com"
PAYMENT_EMAIL="payments@yourorg.com"

POSTGRES_USER="aba_user"
POSTGRES_PASSWORD="supersecurepassword"
POSTGRES_DB="aba_database"
POSTGRES_PORT="5432"

NEVER_SEND_REAL_MAIL="true"
TESTING_EMAIL="your-test-address@example.com"
```

## Default Access

The application includes a default super-user setup for initial access.

- Username: admin@example.com
- Password: Admin1!

Change the password immediately after first login and create any additional admin users you need.

## Notes

- SQLite is used by default for local development.
- PostgreSQL is recommended for production-style deployments.
- The email safety switch helps prevent accidental real-world email sending during testing or staging use.
