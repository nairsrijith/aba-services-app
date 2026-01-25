# Invoice Reminder Feature Documentation

## Overview

The invoice reminder feature allows you to automatically send email reminders to clients for unpaid invoices. You can configure:

1. **Initial Reminder**: Send a reminder X days before the invoice due date
2. **Repeat Reminders**: Optionally send follow-up reminders every X days until the invoice is paid

## Configuration

### Settings Page

Navigate to **Organization Settings** (`/manage/settings`) to configure the invoice reminder feature:

1. **Enable Invoice Reminders**: Toggle to enable/disable the feature
2. **Send Reminder Days Before Due Date**: Number of days before the due date to send the first reminder (default: 5 days)
3. **Enable Repeat Reminders**: Toggle to enable follow-up reminders
4. **Repeat Reminder Every X Days**: Number of days between follow-up reminders (default: 3 days)

### Example Configuration

- Invoice due date: January 30, 2026
- Reminder days: 5
- Repeat enabled: Yes
- Repeat days: 3

**Email Timeline:**
- January 25: First reminder sent (5 days before due date)
- January 28: Second reminder sent (3 days after first)
- January 31: Third reminder sent (3 days after second)
- ... continues until invoice is marked as Paid

## Running the Reminder Processor

The reminder processor checks and sends emails for unpaid invoices. It can be run in several ways:

### 1. Manual CLI Command

Run the reminder processor immediately:

```bash
flask send-invoice-reminders
```

### 2. Cron Job (Recommended)

To run the reminders automatically every hour, add a cron job:

```bash
0 * * * * cd /path/to/aba-services-app && /path/to/.venv/bin/flask send-invoice-reminders
```

Or every 6 hours:

```bash
0 */6 * * * cd /path/to/aba-services-app && /path/to/.venv/bin/flask send-invoice-reminders
```

### 3. Docker Container (Automatic - Recommended)

If running the application in Docker, the cron job is automatically configured during container startup. The invoice reminders will run **every day at 6:00 AM (UTC)** and logs will be written to `/var/log/invoice_reminders.log`.

To change the schedule, modify the cron time in `docker/entrypoint.sh`:

```bash
# Change "0 6" to your desired time (format: minute hour day month weekday)
0 6 * * * cd /myapp && /usr/local/bin/python -m flask send-invoice-reminders >> /var/log/invoice_reminders.log 2>&1
```

Examples:
- `0 9 * * *` - 9:00 AM daily
- `0 12 * * *` - 12:00 PM daily
- `0 6 * * 1` - 6:00 AM every Monday
- `*/30 * * * *` - Every 30 minutes

Then rebuild your Docker image:
```bash
docker compose up --build
```

### 4. View Cron Logs in Docker

To view the cron job logs from running container:

```bash
docker exec <container_name> tail -f /var/log/invoice_reminders.log
```

Or check all container logs:
```bash
docker logs <container_name>
```

### 3. Docker Cron Job

If running in Docker, you can add a background process to the entrypoint:

```bash
# In docker/entrypoint.sh
flask send-invoice-reminders &
```

Or use a scheduler image like [mcuadros/ofelia](https://github.com/mcuadros/ofelia) to schedule the task.

### 4. Background Task Scheduler (Advanced)

For more sophisticated scheduling, consider integrating with:
- **Celery** with Redis/RabbitMQ
- **APScheduler** for Python-based scheduling

## Database Migrations

### Apply Pending Migrations

To set up the invoice reminder feature, apply the pending migrations:

```bash
flask db upgrade
```

This will:
1. Add `invoice_reminder_enabled`, `invoice_reminder_days`, `invoice_reminder_repeat_enabled`, and `invoice_reminder_repeat_days` columns to `app_settings` table
2. Add `last_reminder_sent_date` and `reminder_count` columns to `invoices` table

### Check Migration Status

```bash
flask db current      # Show current migration version
flask db history      # Show migration history
flask db heads        # Show latest migrations
```

## Reminder Email Templates

The reminder emails use the following templates:
- `app/templates/email/invoice_reminder_email.html` - HTML version
- `app/templates/email/invoice_reminder_email.txt` - Text version

These templates receive the following variables:
- `client_name`: Name of the client (parent)
- `invoice_number`: Invoice number
- `invoice_total`: Total invoice amount
- `due_date`: Invoice due date (formatted as "Month DD, YYYY")
- `days_until_due`: Number of days until due
- `reminder_type`: "Due Date Reminder" or "Follow-up Reminder"
- `is_repeat`: Boolean indicating if this is a repeat reminder

## Implementation Details

### Tracking Reminders

Each invoice tracks:
- **last_reminder_sent_date**: Timestamp of the last reminder sent
- **reminder_count**: Total number of reminders sent

This information is automatically updated when reminders are sent.

### Email Integration

Reminders are sent using the existing email system and respect:
- **Gmail OAuth Configuration**: Uses configured Gmail credentials from AppSettings
- **Testing Mode**: If enabled, emails are sent to the testing email instead
- **CC Field**: Reminders are CC'd to the default CC email if configured

### Logging

The reminder processor logs all actions to the application logger:
- When reminders are sent
- Errors or warnings
- Summary of processing

### Code Location

- Invoice reminder logic: `app/utils/invoice_reminder.py`
- CLI command: `app/__init__.py` (see `send-invoice-reminders` command)
- Settings form fields: `app/manage/forms.py` (SettingsForm)
- Settings handler: `app/manage/views.py` (settings view)
- Models: `app/models.py` (Invoice and AppSettings models)

## Troubleshooting

### Reminders Not Sending

1. **Check if reminders are enabled** in Organization Settings
2. **Verify Gmail OAuth is configured** - Reminders won't send without valid Gmail credentials
3. **Check application logs** for error messages
4. **Verify invoice status** - Only unpaid invoices receive reminders

### Testing Reminders

To test the reminder functionality:

1. Go to Organization Settings
2. Enable "Enable Email Testing Mode" and set a test email
3. Enable invoice reminders with short intervals
4. Create or update an invoice with a due date 5 days from now
5. Run: `flask send-invoice-reminders`
6. Check the test email for the reminder

### Stopping Reminders

To stop sending reminders for an invoice, simply:
- Mark the invoice as "Paid" in the invoices list
- Or disable reminders globally in Organization Settings

## Future Enhancements

Possible improvements to the reminder system:
- SMS reminders via Twilio
- Reminder history/audit log
- Per-client reminder preferences
- Custom reminder message templates
- Conditional reminders based on payment status
- Automated payment link in reminder emails
