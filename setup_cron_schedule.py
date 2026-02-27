#!/usr/bin/env python3
"""
Helper script to set up cron schedule for invoice reminders based on settings.
Reads the invoice_reminder_time from the database and updates the crontab.
"""
import os
import sys
import subprocess
from app import create_app, db
from app.models import AppSettings


def get_reminder_time():
    """Get the reminder time from AppSettings, fallback to 06:00 if not set."""
    try:
        settings = AppSettings.query.first()
        if settings and settings.invoice_reminder_time:
            return settings.invoice_reminder_time
    except Exception as e:
        print(f"Warning: Could not read reminder time from database: {e}", file=sys.stderr)
    
    return '06:00'  # Default to 6 AM


def parse_time_to_cron(time_str):
    """
    Parse time string (HH:MM) and return cron format (minute hour).
    
    Args:
        time_str: Time in HH:MM format (24-hour)
        
    Returns:
        Tuple of (minute, hour) for cron schedule
    """
    try:
        parts = time_str.split(':')
        if len(parts) != 2:
            raise ValueError(f"Invalid time format: {time_str}")
        
        hour = int(parts[0])
        minute = int(parts[1])
        
        if not (0 <= hour <= 23) or not (0 <= minute <= 59):
            raise ValueError(f"Invalid time values: hour={hour}, minute={minute}")
        
        return minute, hour
    except (ValueError, IndexError) as e:
        print(f"Error parsing time '{time_str}': {e}", file=sys.stderr)
        return 0, 6  # Fallback to 6 AM


def setup_cron_schedule():
    """Set up the cron schedule based on invoice_reminder_time."""
    app = create_app()
    
    with app.app_context():
        reminder_time = get_reminder_time()
        minute, hour = parse_time_to_cron(reminder_time)
        
        python_bin = os.environ.get('PYTHON_BIN', '/usr/bin/python')
        
        # Cron format: minute hour day month weekday
        # * * * * * means every minute, every hour, every day, every month, every weekday
        cron_schedule = f"{minute} {hour} * * *"
        cron_entry = f"{cron_schedule} cd /myapp && {python_bin} /myapp/send_reminders.py >> /var/log/invoice_reminders.log 2>&1"
        
        print(f"Setting cron schedule to: {cron_schedule} (time: {reminder_time})")
        print(f"Cron entry: {cron_entry}")
        
        try:
            # Add the cron entry
            process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate(input=cron_entry.encode())
            
            if process.returncode != 0:
                print(f"Error setting crontab: {stderr.decode()}", file=sys.stderr)
                return False
            
            print("Cron schedule set successfully")
            return True
        except Exception as e:
            print(f"Error setting up cron: {e}", file=sys.stderr)
            return False


if __name__ == '__main__':
    success = setup_cron_schedule()
    sys.exit(0 if success else 1)
