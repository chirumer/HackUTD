#!/usr/bin/env python3
"""Send a test SMS using credentials in .env.

Reads the following environment variables (from system env or .env):
 - TWILIO_ACCOUNT_SID
 - TWILIO_AUTH_TOKEN
 - TWILIO_PHONE_NUMBER  (the destination phone number, E.164)
 - TWILIO_FROM_NUMBER  (optional; a Twilio-capable sender number in E.164)

Usage:
  - Edit `scripts/.env` to include TWILIO_FROM_NUMBER if you want a different sender.
  - Run: `./.venv/bin/python send_message.py` or activate venv and `python send_message.py`.

Be careful: thi s will send a live SMS when executed.
"""
import os
import sys
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
to_number = os.environ.get('TWILIO_PHONE_NUMBER')
from_number = os.environ.get('TWILIO_FROM_NUMBER', os.environ.get('TWILIO_PHONE_NUMBER'))

if not account_sid or not auth_token or not to_number:
    sys.exit('Error: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER must be set in the environment or in a .env file.')

DEFAULT_BODY = "Test message from scripts/send_message.py"

def main():
    body = DEFAULT_BODY
    # Allow an optional message via first CLI arg
    if len(sys.argv) > 1:
        body = sys.argv[1]

    client = Client(account_sid, auth_token)

    print(f'Sending message from {from_number} -> {to_number}')
    try:
        message = client.messages.create(
            body=body,
            from_=from_number,
            to=to_number,
        )
        print('Message sent, SID:', message.sid)
        print('Status:', getattr(message, 'status', 'unknown'))
    except Exception as e:
        print('Error sending message:', e)
        raise

if __name__ == '__main__':
    main()
