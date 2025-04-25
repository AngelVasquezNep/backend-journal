import logging
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class Senders(Enum):
    AWS = "AWS"
    GMAIL = "GMAIL"


class EmailSender:
    def __init__(self, provider: Senders):
        match provider:
            case Senders.GMAIL:
                from .gmail import GmailService
                self.sender = GmailService()
            case Senders.AWS:
                from .aws_ses import AWSEmailService
                self.sender = AWSEmailService()
            case _:
                raise NotImplementedError(f"Provider {provider} not implemented")

    def send_message(
        self,
        To,
        Subject: Optional[str] = None,
        Content: Optional[str] = None,
    ):
        return self.sender.send_message(To, Subject, Content)
