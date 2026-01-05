
# ABA Services Web Application

This web application is designed to help ABA service providers manage their business operations, including client and employee records, session tracking, invoicing, and payroll. It is suitable for small businesses and organizations providing Applied Behavior Analysis (ABA) services to special needs clients.

## Features

- **Employee Management**
   - Add, update, activate/deactivate employees
   - Assign designations and pay rates
   - Cascade deactivation to supervised clients
   - Group employees by active/inactive status

- **Client Management**
   - Onboard new clients with supervision and therapy rates
   - Assign supervisors (Behavior Analysts)
   - Activate/deactivate clients (with safety checks for unpaid invoices)
   - Group clients by active/inactive status

- **Session Management**
   - Add, update, delete therapy and supervision sessions
   - Calendar view for visualizing and scheduling sessions
   - File attachments for session documentation
   - Future date scheduling capabilities
   - Bulk upload and delete operations
   - Role-based access control for session management
   - Calendar view for scheduling and viewing sessions by client or employee
   - Attach files to sessions (e.g., session notes, reports)
   - Schedule sessions in advance (future dates allowed)
   - Click on calendar dates to quickly add new sessions
   - Bulk delete sessions with dependency checks

- **Invoicing**
   - Generate invoices for clients based on session data and activity rates
   - Download invoices as PDF
   - Invoice status workflow: Draft, Sent, Paid
   - Color-coded status badges and tooltips
   - Mark invoices as sent/paid, with confirmation modals
   - Prevent deletion of invoices unless in draft status
   - Send email automatically upon marking the email as Sent or Paid
   - Send ad-hoc email with invoice

- **Payroll & Paystubs**
   - Generate paystubs based on sessions and rates
   - Download paystubs as PDF
   - Automatically send emails to employee when the paystub is created
   - Send ad-hoc email with paystub to employee

- **Security & Access Control**
   - User roles: super user, admin, therapist (previously called "user"), supervisor
   - CSRF protection for all forms
   - Login and registration with activation key

- **Admin Tools**
   - CLI script for bulk activation/deactivation (`scripts/manage_activation.py`)
   - Designation and activity management
   - Manage pay rates for employees
   - User login management
   - Organization settings management to update name, address, log etc
   - Email OAuth settings to send outgoing emails using Gmail
   - Setting app into email testing mode to prevent mails from been sent to actual client or employee 

- **Data & Reporting**
   - Persistent storage using SQLite (default) or Postgres
   - Data grouped and filtered by active/inactive status
   - Toggle to show/hide inactive records
   - Calendar view for session visualization
   - Dashboard with key statistics and metrics

## Setup & Deployment

### 1. Pull and Run the Docker Image

The app is available as a pre-built Docker image:
https://hub.docker.com/r/nairsrijith/abawebapp

#### Steps:

1. **Create a directory** for the app and persistent data:
    ```sh
    mkdir abawebapp && cd abawebapp
    ```
2. **Copy the `docker-compose.yml` file** into your directory.
3. **Create an environment file** (optional, recommended):
    - Create a file named `.env` in the same directory with the following variables:
       ```env
       # These will be used in invoices and branding.
       ORG_NAME="Your Organization Name"
       ORG_ADDRESS="123 Main St, City, State"
       ORG_PHONE="555-123-4567"
       ORG_EMAIL="info@yourorg.com"
       PAYMENT_EMAIL="payments@yourorg.com"
       
       POSTGRES_USER="database_user"
       POSTGRES_PASSWORD="supersecurepassword"
       POSTGRES_DB="app_database"
       POSTGRES_PORT="5432"
       ```
4. **Edit `docker-compose.yml`** as needed:
    - Change the host port (left side of `1234:8080`) to your preferred port.
    - Ensure the volume mapping (`./db_data:/var/lib/postgresql/data`, `./data:/myapp/app/data`, `./assets/logo.png:/myapp/app/static/images/logo.png`) points to a persistent location.
5. **Start the app:**
    ```sh
    docker compose up -d
    ```

### 2. Initial Login

After deployment, access the app in your browser at `http://localhost:1234` (or your chosen port).

Default super user credentials:
```
username: admin@example.com
password: Admin1!
```
**Change the password immediately after first login.**
**Create additional Admin user(/s)** 

## User Roles & Permissions

- **Super**: Can create other accounts and perform full system maintenance.
- **Admin**: Can manage employees, clients, sessions, invoices, paystubs and system configuration.
- **Therapist**: Can manage their own sessions and view the parts of the app assigned to therapists. Default role for 'Therapist' and 'Senior Therapist'
- **Supervisor**: Supervisors can add and manage sessions for their supervised clients and may assign those sessions to any employee. Default role for 'Behaviour Analyst'
- Users/Employees with "Therapist" or "Senior Therapist" or "Behaviour Analyst" position can be promoted from their initial role to Admin and demoted back to default role.

## Onboarding Workflow

1. **Add Employees**
    - Go to Employees section, add new employee, assign designation and pay rate.
    - Activate/deactivate employees as needed.

2. **Add Clients**
    - Go to Clients section, onboard new client.
    - You cannot add a client without a Behaviour Analyst (Supervisor) in Employee Record.
    - Assign supervisor and set rates for supervision/therapy.
    - Activate/deactivate clients as needed.

3. **Add Sessions**
   - Record sessions for clients, specifying activity type and duration.
   - Use the calendar view to visualize existing sessions and click on dates to add new ones.
   - Attach files (e.g., session notes) to sessions.
   - Schedule sessions in advance for future dates.
   - Admins can manage sessions for all; Therapists can manage sessions for themselves; Supervisors can create/manage sessions for clients they supervise and assign the delivering employee to any Therapist or Senior Therapist.

4. **Generate Invoices**
    - Select client and date range to generate invoice based on sessions.
    - Review invoice, download PDF, and share with client.
    - Mark invoice as sent/paid; status is shown with color-coded badges.
    - Only draft invoices can be deleted.
    - Emails are sent to the primary and secondary email for client.
    - Invoice PDFs are sent automatically via email when the invoice status is updated to Sent or Paid.
    - Emails can be sent on ad-hoc basis as well.

5. **Generate Paystubs**
    - Go to Payroll section, select employee and date range.
    - Generate paystub based on sessions and pay rates.
    - Download paystub as PDF.
    - Paystub PDF is sent to the employee as soon as it is generated.
    - Ad-hoc emails can be sent for the Paystub as well.

## Activation & Deactivation

- Employees and clients can be activated/deactivated from the list views.
- Deactivation checks for dependencies (e.g., active clients, unpaid invoices).

## Data Persistence

- All data is stored in SQLite by default, mapped to the `./data` directory (or your chosen volume).
- Back up the data directory regularly for disaster recovery.

## Security

- All forms are protected with CSRF tokens.
- User registration requires activation key (admin/super user only).
- Passwords should be changed after initial setup.

## Support & Customization

- For advanced configuration, update environment variables in `.env` or `docker-compose.yml`.
- To use a different database, modify the code and rebuild the Docker image.
