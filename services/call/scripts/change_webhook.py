import os
from twilio.rest import Client
from dotenv import load_dotenv
import sys
import argparse

# Load environment variables from .env if present
load_dotenv()

# Parse command line arguments
parser = argparse.ArgumentParser(description='Update Twilio voice webhook URL')
parser.add_argument('--url', type=str, help='New webhook URL (overrides TWILIO_VOICE_URL from .env)')
args = parser.parse_args()

# Read credentials and settings from environment variables
account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
# Prefer the Twilio-owned sender/incoming number if provided; fall back to TWILIO_PHONE_NUMBER
phone_number = os.environ.get('TWILIO_FROM_NUMBER') or os.environ.get('TWILIO_PHONE_NUMBER')  # E.164 format
voice_url = args.url or os.environ.get('TWILIO_VOICE_URL')

if not account_sid or not auth_token or not phone_number:
  sys.exit('Error: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and TWILIO_FROM_NUMBER or TWILIO_PHONE_NUMBER must be set in the environment or in a .env file.')

if not voice_url:
  sys.exit('Error: TWILIO_VOICE_URL must be set in .env or provided via --url argument.')

client = Client(account_sid, auth_token)

try:
  print(f'Looking up incoming phone number {phone_number}...')
  nums = client.incoming_phone_numbers.list(phone_number=phone_number)
  if not nums:
    raise RuntimeError(f'No IncomingPhoneNumber found for {phone_number} in this Twilio account.')

  ipn = nums[0]
  print(f'Found IncomingPhoneNumber SID={ipn.sid}, friendly_name={getattr(ipn, "friendly_name", None)}')

  print(f'Updating voice webhook for {phone_number} -> {voice_url}')
  # Update the incoming phone number's voice webhook by SID
  incoming_phone_number = client.incoming_phone_numbers(ipn.sid).update(voice_url=voice_url)

  # Print a confirmation
  print('Update successful. Friendly name:', getattr(incoming_phone_number, 'friendly_name', repr(incoming_phone_number)))
except Exception as e:
  print('Error while updating Twilio incoming phone number:', e)
  raise
