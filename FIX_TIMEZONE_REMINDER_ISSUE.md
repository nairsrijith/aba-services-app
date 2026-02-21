# Fix for Invoice Reminder Not Matching Today's Due Date

## Problem
When running the invoice reminder script on a containerized application in a different server/timezone, invoices due today were not being matched for sending reminders, even though the database was being updated with reminder sent dates.

## Root Cause
The issue is **timezone mismatch**: 
- The containerized application was running in **UTC timezone** (or a different timezone)
- The invoice due dates were created in a **different local timezone** (e.g., EST, Toronto, etc.)
- The date comparison `(invoice.payby_date - datetime.now().date())` was using local system time, which could differ by a day

**Example:**
- Invoice due date: **2026-02-21** (in EST timezone, UTC-5)
- Server time: **2026-02-21 20:00 EST** = **2026-02-22 01:00 UTC**
- `datetime.now().date()` in UTC returns **2026-02-22**
- Calculation: `2026-02-21 - 2026-02-22 = -1 day`
- Result: Reminder NOT sent (because `-1 < 0`)

## Solution Implemented

### Fix 1: Use UTC Consistently in Code (RECOMMENDED)
Modified `app/utils/invoice_reminder.py` to use `datetime.utcnow()` instead of `datetime.now()`:

**Changes:**
1. Updated `should_send_first_reminder()` - uses `datetime.utcnow().date()` for comparison
2. Updated `should_send_repeat_reminder()` - uses `datetime.utcnow().date()` and `datetime.utcnow()`
3. Updated `send_invoice_reminder()` - uses `datetime.utcnow().date()` for all date calculations
4. Updated timestamp storage - uses `datetime.utcnow()` instead of `datetime.now()`

This ensures all date comparisons are timezone-independent and work correctly regardless of where the server is running.

### Fix 2: Set Container Timezone (OPTIONAL - for local timezone preference)
Updated `docker-compose.yml` and `Dockerfile`:

**docker-compose.yml:**
```yaml
environment:
  TZ: ${TZ:-America/Toronto}  # Set to your organization's timezone
```

**Dockerfile:**
- Added `tzdata` to system packages so timezone database is available

This allows you to set the container to run in your local timezone instead of UTC.

## How to Use

### Option A: Use UTC Consistently (No changes needed to deployment)
The code fix is already in place. Simply rebuild and redeploy your Docker image:

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

Then test the cron job:
```bash
docker exec <container_name> flask send-invoice-reminders
```

### Option B: Set Specific Timezone (If you prefer local time)
1. Add or update `TZ` variable in your `.env` file:
```bash
TZ=America/Toronto  # Use your timezone
```

2. Rebuild the Docker image:
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

Common timezone values:
- `America/Toronto` - Eastern Time (Canada)
- `America/New_York` - Eastern Time (US)
- `America/Los_Angeles` - Pacific Time
- `America/Chicago` - Central Time
- `UTC` - UTC timezone
- See [IANA timezone database](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) for full list

## Testing

Run the diagnostic script to verify the fix:

```bash
# On your server, inside the project directory:
python3 diagnose_reminder_issue.py
```

This will show:
- Current server date/time
- All invoices with "Sent" status
- For each invoice: whether it should trigger a reminder
- Detailed condition checks for debugging

Expected output for an invoice due today:
```
Invoice INV-001:
  Status: Sent
  Due Date: 2026-02-21
  Current Date: 2026-02-21
  Days Until Due: 0
  Should send FIRST reminder: True
```

### Manual Testing
```bash
# Run the reminder script manually:
docker exec <container_name> flask send-invoice-reminders

# Or:
docker exec <container_name> python send_reminders.py

# Check logs:
docker logs <container_name> | grep -i invoice
```

## What Changed in Code

### before (Timezone-dependent):
```python
days_until_due = (invoice.payby_date - datetime.now().date()).days
```

### after (Timezone-independent):
```python
utc_today = datetime.utcnow().date()
days_until_due = (invoice.payby_date - utc_today).days
```

## Benefits

1. **Consistent across servers**: Works correctly regardless of server location or timezone
2. **No deployment changes needed**: Works with UTC timezone (Docker default) without reconfiguration
3. **Backward compatible**: Existing invoices and reminder tracking continue to work
4. **Proper logging**: Debug logs show exactly what dates are being compared

## Troubleshooting

**Issue: Still not matching invoices**
- Run the `diagnose_reminder_issue.py` script to see exact date comparisons
- Verify invoices have status `'Sent'`, not `'Paid'`
- Check if `reminder_count` is 0 (for first reminders)

**Issue: Getting too many or too few reminders**
- Check the `invoice_reminder_days` setting in AppSettings (Settings page)
- Verify `invoice_reminder_repeat_enabled` status if seeing repeat reminders

**Issue: Invoices marked as overdue incorrectly**
- Verify invoice `payby_date` is stored correctly in database
- Run `diagnose_reminder_issue.py` to check date calculations
