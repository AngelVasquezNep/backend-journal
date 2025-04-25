import os.path
import base64
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.message import EmailMessage
from .interface import EmailServiceInterface


logger = logging.getLogger(__name__)



# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]


class GmailService(EmailServiceInterface):
    @staticmethod
    def _get_creds() -> Credentials:
        # creds: Credentials = service_account.Credentials.from_service_account_file("credentials.service_account.json", scopes=SCOPES)
        # return creds
        creds = None
        if os.path.exists("token.json"):
            creds: Credentials = Credentials.from_authorized_user_file("token.json", SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file("credentials.owner.json", SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open("token.json", "w") as token:
                token.write(creds.to_json())
        return creds

    @staticmethod
    def service() -> None:
        creds = GmailService._get_creds()
        return build("gmail", "v1", credentials=creds)

    @staticmethod
    def send_message(
        To,
        Subject=None,
        Content=None,
    ):
        service = GmailService.service()
        message = EmailMessage()

        message.set_content(Content)

        message["To"] = To
        # message["From"] = From
        message["Subject"] = Subject

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        create_message = {"raw": encoded_message}
        send_message = (
            service.users()
            .messages()
            .send(userId="me", body=create_message)
            .execute()
        )
        logger.info(f'Message Id: {send_message["id"]} sent to "{To}" with subject "{Subject}" and content "{Content}"')
        return send_message
