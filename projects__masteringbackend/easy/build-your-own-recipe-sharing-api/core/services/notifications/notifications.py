import logging
from typing import Optional
from core.services.email import EmailSender, Senders

logger = logging.getLogger(__name__)


class NotificationsService:
    @staticmethod
    def send_one(
            recipient,
            subject: Optional[str] = None,
            body: Optional[str] = None,):
        raise NotImplementedError(
            "send_notification method is not implemented")

    @staticmethod
    def send_many(recipients, body):
        for recipient in recipients:
            NotificationsService.send_one(recipient, body)


class EmailService(NotificationsService):
    @staticmethod
    def send_one(recipient,
                 subject: Optional[str] = None,
                 body: Optional[str] = None,):
        EmailSender(Senders.AWS).send_message(recipient, subject, body)
