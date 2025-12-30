#!/usr/bin/env python3
"""
Script to obtain Gmail OAuth refresh token for sending emails.

Usage:
1. Set up OAuth credentials in Google Cloud Console as 'Desktop application'.
2. Enable Gmail API for your project.
3. Download the credentials JSON file.
4. Run this script with the path to the JSON file.

The script will open a browser for authorization and print the refresh token.
Save the refresh token securely in your app settings.
"""

import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def main():
    if len(sys.argv) != 2:
        print("Usage: python get_refresh_token.py <path_to_credentials.json>")
        sys.exit(1)

    creds_file = sys.argv[1]

    flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
    creds = flow.run_local_server(port=0)

    print("Refresh token:", creds.refresh_token)
    print("Client ID:", creds.client_id)
    print("Client Secret:", creds.client_secret)

if __name__ == '__main__':
    main()