# Fix for Invoice Reminder Email Not Sending

## Problem
The cron job was successfully updating the invoice table with reminder sent dates and counts, but no emails were being sent to the client's parent email address.

## Root Cause
The issue was in the background email thread handling in `app/utils/email_utils.py`:

1. **Daemon threads were being killed**: The `queue_email()` function was creating daemon threads (`daemon=True`), which get terminated when the main process exits. When the invoice reminder cron job completed, the daemon threads were killed before they could send the emails.

2. **No exception handling in background threads**: Any exceptions that occurred in the background thread were silently swallowed because there was no try/except block in the `send_in_thread()` function.

3. **No wait mechanism**: The `process_invoice_reminders()` function didn't wait for background emails to complete before returning, so the script would exit immediately after queuing emails.

## Changes Made

### 1. Modified `app/utils/email_utils.py`:

- **Changed daemon threads to non-daemon**: Changed `daemon=True` to `daemon=False` so threads are not terminated when the main process exits.

- **Added thread tracking**: Created a module-level `_active_email_threads` list to keep track of all background email threads.

- **Added exception handling**: Wrapped the background send operation in try/except to catch and log any exceptions.

- **Added `wait_for_pending_emails()` function**: New function to wait for all pending email threads to complete with a configurable timeout.

- **Improved Gmail API logging**: Enhanced logging in `_send_via_gmail_api()` to provide better diagnostics:
  - Log when Gmail credentials are missing
  - Log HTTP errors separately from other exceptions
  - Added debug logging for API requests
  - Better error messages

### 2. Modified `app/utils/invoice_reminder.py`:

- **Added wait for emails**: The `process_invoice_reminders()` function now calls `wait_for_pending_emails()` to wait for all queued emails to be sent before returning.

- **Improved logging**: Enhanced logging to show when emails are queued and when tracking is updated.

## How It Works Now

1. When `process_invoice_reminders()` is called:
   - It finds unpaid invoices that need reminders
   - For each invoice needing a reminder, it calls `send_invoice_reminder()`
   - That function queues the email (which returns immediately)
   - The database is updated with the reminder count and date

2. **After all reminders are queued:**
   - The function calls `wait_for_pending_emails(timeout=30.0)`
   - This waits for all background email threads to complete
   - If any thread takes too long, it logs a warning but continues
   - Only after all threads complete (or timeout), the function returns

3. **Logging:**
   - Each step is now logged with INFO or ERROR level
   - Any exceptions in background threads are logged with full stack traces
   - The cron logs will now show exactly what happened with each email

## Testing

To verify the fix works:

```bash
cd /home/vsrijith/Projects/aba-services-app
source .venv/bin/activate
flask send-invoice-reminders
```

Check the logs to see detailed output about email sending.

## Expected Behavior

When the cron job runs, you should now see logs like:

```
Invoice INV-001: Email queued successfully to ['client@example.com']
Invoice INV-001: Sending email via Gmail API to client@example.com subject=Due Date Reminder: Invoice INV-001
Invoice INV-001: Email sent via Gmail API successfully, message ID: ...
Invoice INV-001: Reminder tracking updated (count: 1)
Waiting for all queued emails to be sent...
Email thread 1/1 completed
All emails sent successfully
```

If there are any issues, they will now be captured in the logs instead of silently failing.
