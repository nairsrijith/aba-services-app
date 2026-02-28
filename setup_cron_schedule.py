#!/usr/bin/env python3
"""
Helper script to set up cron schedule for invoice reminders based on settings.
Reads the invoice_reminder_time from the database and updates the crontab.
"""
import os
import sys
import time
import signal
import subprocess
from datetime import datetime
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
        
        python_bin = os.environ.get('PYTHON_BIN', '/usr/local/bin/python')
        
        # Ensure log directory exists and is writable
        log_dir = '/var/log'
        try:
            os.makedirs(log_dir, exist_ok=True)
            # Touch the log file to ensure it exists and is writable
            log_file = os.path.join(log_dir, 'invoice_reminders.log')
            with open(log_file, 'a') as f:
                f.write(f"\n--- Cron schedule updated at {datetime.now().isoformat()} ---\n")
            print(f"Log file ensured at {log_file}")
        except Exception as e:
            print(f"Warning: Could not create log file: {e}", file=sys.stderr)
        
        # Cron format: minute hour day month weekday
        cron_schedule = f"{minute} {hour} * * *"
        # Build environment header for crontab so the job sees the same variables
        # Build environment header for crontab so the job sees the same variables
        env_lines = ""
        for k, v in os.environ.items():
            # cron entries cannot handle newlines; skip any weird values
            if "\n" in v:
                continue
            env_lines += f"{k}={v}\n"
        # Ensure PATH and PYTHONUNBUFFERED at minimum (may already be in env_lines)
        if 'PATH=' not in env_lines:
            env_lines += "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\n"
        if 'PYTHONUNBUFFERED=' not in env_lines:
            env_lines += "PYTHONUNBUFFERED=1\n"
        cron_entry = (
            f"{env_lines}"
            f"{cron_schedule} cd /myapp && {python_bin} /myapp/send_reminders.py >> /var/log/invoice_reminders.log 2>&1\n"
        )
        
        print(f"Setting cron schedule to: {cron_schedule} (time: {reminder_time})")
        print("Cron entry installed (only showing job line):", cron_entry.strip().splitlines()[-1])
        
        try:
            # Add the cron entry (crontab requires newline at EOF)
            process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate(input=cron_entry.encode())
            
            if process.returncode != 0:
                error_msg = stderr.decode().strip()
                print(f"Error setting crontab: {error_msg}", file=sys.stderr)
                return False
            
            print("Cron schedule set successfully")
            
            # Send SIGHUP signal to cron daemon if it's running, to reload the crontab.
            # If cron is not yet running (initial setup), this is a no-op and that's OK.
            # The cron daemon will read the crontab when it starts.
            try:
                result = subprocess.run(['pgrep', '-f', 'crond'], capture_output=True, text=True)
                if result.returncode == 0:
                    cron_pid = result.stdout.strip().split('\n')[0]
                    os.kill(int(cron_pid), 1)  # SIGHUP = 1
                    print(f"Sent SIGHUP to cron daemon (PID {cron_pid}) to reload crontab")
                else:
                    print("Cron daemon not yet running (will read crontab on startup)")
            except Exception as e:
                print(f"Note: Could not signal cron daemon (OK if starting): {e}")
            
            return True
        except Exception as e:
            print(f"Error setting up cron: {e}", file=sys.stderr)
            return False


if __name__ == '__main__':
    success = setup_cron_schedule()
    sys.exit(0 if success else 1)
