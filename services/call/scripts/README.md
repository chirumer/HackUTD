# scripts/

This folder contains helper scripts and a per-folder virtual environment.

Created artifacts
- `.venv/` — virtual environment created in this folder.
- `requirements.txt` — pinned packages installed into `.venv` (created after installation).

How to use the venv

Option A (preferred, explicit):

    ./ .venv/bin/python change_webhook.py

Option B (activate the venv):

    source .venv/bin/activate
    python change_webhook.py
    deactivate

Notes and safety
- `change_webhook.py` uses the Twilio API and will perform a live update on an incoming phone number when run. This will change your Twilio configuration if valid credentials are present.
- For safety, set the following environment variables before running the script instead of keeping credentials in the file:
  - `TWILIO_ACCOUNT_SID`
  - `TWILIO_AUTH_TOKEN`

  Example (macOS / zsh):

      export TWILIO_ACCOUNT_SID="AC..."
      export TWILIO_AUTH_TOKEN="your_auth_token"
      ./ .venv/bin/python change_webhook.py

- Consider removing hard-coded credentials from `change_webhook.py` and using env vars or a secure secret store.

If you want me to run `change_webhook.py` now, please confirm that you consent to a live Twilio API call and that the credentials present (if any) are intended for this action. If you prefer, I can run the script in a dry-run/simulated mode or with safe mocking instead.
