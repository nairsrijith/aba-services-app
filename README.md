
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
   - Record therapy and supervision sessions
   - CRUD operations for sessions (admin and user roles)
   - Categorize sessions by activity type

- **Invoicing**
   - Generate invoices for clients based on session data and activity rates
   - Download invoices as PDF
   - Invoice status workflow: Draft, Sent, Paid
   - Color-coded status badges and tooltips
   - Mark invoices as sent/paid, with confirmation modals
   - Prevent deletion of invoices unless in draft status

- **Payroll & Paystubs**
   - Manage pay rates for employees
   - Generate paystubs based on sessions and rates
   - Download paystubs as PDF

- **Security & Access Control**
   - User roles: super user, admin, therapist (previously called "user"), supervisor
   - CSRF protection for all forms
   - Login and registration with activation key

- **Admin Tools**
   - CLI script for bulk activation/deactivation (`scripts/manage_activation.py`)
   - Designation and activity management

- **Data & Reporting**
   - Persistent storage using SQLite (default)
   - Data grouped and filtered by active/inactive status
   - Toggle to show/hide inactive records

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
       ORG_NAME="Your Organization Name"
       ORG_ADDRESS="123 Main St, City, State"
       ORG_PHONE="555-123-4567"
       ORG_EMAIL="info@yourorg.com"
       PAYMENT_EMAIL="payments@yourorg.com"
       ```
    - These will be used in invoices and branding.
4. **Edit `docker-compose.yml`** as needed:
    - Change the host port (left side of `1234:8080`) to your preferred port.
    - Ensure the volume mapping (`./data:/myapp/app/data`) points to a persistent location.
5. **Start the app:**
    ```sh
    docker compose up -d
    ```

#### Example `docker-compose.yml` snippet:
```yaml
version: '3.8'
services:
   abawebapp:
      image: nairsrijith/abawebapp:latest
      ports:
         - "1234:8080"
      env_file:
         - .env
      volumes:
         - ./data:/myapp/app/data
```

### 2. Initial Login

After deployment, access the app in your browser at `http://localhost:1234` (or your chosen port).

Default super user credentials:
```
username: admin@example.com
password: Admin1!
```
**Change the password immediately after first login.**

## User Roles & Permissions

- **Super User**: Can create other accounts and perform full system maintenance.
- **Admin**: Can manage employees, clients, sessions, invoices, paystubs and system configuration.
- **Therapist**: (renamed from the old "user" role) Can manage their own sessions and view the parts of the app assigned to therapists.
- **Supervisor**: A supervisor is typically an employee with the designation "Behaviour Analyst". Supervisors can add and manage sessions for their supervised clients and may assign those sessions to any employee with a Therapist or Senior Therapist designation.

Note: to enable supervisor functionality, create a user account for the supervisor and ensure the account email matches the `email` field on the corresponding `employees` record. The application maps the logged-in user to the employee record by email to determine supervised clients.

## Onboarding Workflow

1. **Add Employees**
    - Go to Employees section, add new employee, assign designation and pay rate.
    - Activate/deactivate employees as needed.
    - Assign employees as supervisors to clients.

2. **Add Clients**
    - Go to Clients section, onboard new client.
    - Assign supervisor (Behavior Analyst) and set rates for supervision/therapy.
    - Activate/deactivate clients as needed.

3. **Add Sessions**
   - Record sessions for clients, specifying activity type and duration.
   - Admins can manage sessions for all; Therapists can manage sessions for themselves; Supervisors can create/manage sessions for clients they supervise and assign the delivering employee to any Therapist or Senior Therapist.

4. **Generate Invoices**
    - Select client and date range to generate invoice based on sessions.
    - Review invoice, download PDF, and share with client.
    - Mark invoice as sent/paid; status is shown with color-coded badges.
    - Only draft invoices can be deleted.

5. **Generate Paystubs**
    - Go to Payroll section, select employee and date range.
    - Generate paystub based on sessions and pay rates.
    - Download paystub as PDF.

## Activation & Deactivation

- Employees and clients can be activated/deactivated from the list views.
- Deactivation checks for dependencies (e.g., active clients, unpaid invoices).

### Notes about the role rename (existing deployments)

If you are updating an existing deployment, user accounts created previously will have their role stored as the string `user`.
The application code has been updated to treat that legacy value as the new `therapist` role. To permanently migrate the database rows you can run a small SQL update against the app database before restarting the app:

For SQLite (example):

```sql
UPDATE users SET user_type = 'therapist' WHERE user_type = 'user';
```

Or from Python within the app context (quick one-off script):

```py
from app import app, db
from app.models import User

with app.app_context():
   db.session.execute("UPDATE users SET user_type = 'therapist' WHERE user_type = 'user'")
   db.session.commit()
```

Make a backup of your database before performing this migration.


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
