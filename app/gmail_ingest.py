"""
Gmail ingestion — polls an inbox for unread invoice attachments,
runs each through the same normalize -> extract -> triage pipeline
used by the upload API, then marks the email read.

Scope is gmail.modify, not full access: this script can read
messages and mark them read. It cannot send email, delete anything,
or touch anything outside what it needs.

First run opens a browser for OAuth consent. After that, the token
is cached in credentials/gmail_token.json and reused, refreshing
automatically when it expires.

    python -m app.gmail_ingest
"""
import base64
import os
import tempfile

from dotenv import load_dotenv
load_dotenv()

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.normalize import normalize_to_png
from app.extract import extract_invoice
from app.validate import triage

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
CREDENTIALS_PATH = os.path.expanduser("~/Invoice-triage/credentials/gmail_credentials.json")
TOKEN_PATH = os.path.expanduser("~/Invoice-triage/credentials/gmail_token.json")

# Narrow on purpose: unread, with an attachment, filename ending in
# pdf/png/jpg. This isn't scanning the whole inbox.
QUERY = 'is:unread has:attachment (filename:pdf OR filename:png OR filename:jpg) from:vincentedeh42@gmail.com subject:"invoice test"'


def get_credentials():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            flow.redirect_uri = "http://localhost"
            auth_url, _ = flow.authorization_url(prompt="consent")
            print("\nOpen this URL in any browser and approve access:\n")
            print(auth_url)
            print("\nThe browser will then try to load a page that fails (e.g. \"localhost refused to connect\"). That's expected.")
            print("Copy the FULL URL from the browser address bar at that point and paste it below.\n")
            redirect_response = input("Paste the full redirect URL here: ").strip()
            flow.fetch_token(authorization_response=redirect_response)
            creds = flow.credentials
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return creds


def poll_and_process(provider: str = "openrouter"):
    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds)

    results = service.users().messages().list(userId="me", q=QUERY).execute()
    messages = results.get("messages", [])
    print(f"Found {len(messages)} matching message(s).")

    for msg_meta in messages:
        msg_id = msg_meta["id"]
        msg = service.users().messages().get(userId="me", id=msg_id).execute()

        subject = next(
            (h["value"] for h in msg["payload"]["headers"] if h["name"] == "Subject"),
            "(no subject)",
        )
        print(f"\nProcessing: {subject}")

        for part in msg["payload"].get("parts", []):
            filename = part.get("filename", "")
            ext = os.path.splitext(filename)[1].lower()
            if ext not in {".pdf", ".png", ".jpg", ".jpeg"}:
                continue

            attachment_id = part["body"].get("attachmentId")
            if not attachment_id:
                continue

            attachment = (
                service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=msg_id, id=attachment_id)
                .execute()
            )
            file_data = base64.urlsafe_b64decode(attachment["data"])

            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                    tmp.write(file_data)
                    tmp_path = tmp.name

                png_path = normalize_to_png(tmp_path)
                extraction = extract_invoice(png_path, provider=provider)
                result = triage(extraction)

                print(f"  Vendor:  {extraction.vendor.name}")
                print(f"  Invoice: {extraction.invoice.number}")
                print(f"  Status:  {result.status.upper()}")
                for flag in result.flags:
                    print(f"    [{flag.severity.upper()}] {flag.type}: {flag.message}")

            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)
                if tmp_path:
                    png_guess = os.path.splitext(tmp_path)[0] + ".png"
                    if os.path.exists(png_guess) and png_guess != tmp_path:
                        os.remove(png_guess)

        # Mark read so the next poll doesn't pick this up again
        service.users().messages().modify(
            userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
        ).execute()
        print("  Marked read.")


if __name__ == "__main__":
    poll_and_process()
