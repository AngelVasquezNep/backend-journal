import boto3
from botocore.exceptions import ClientError

from .interface import EmailServiceInterface


class AWSEmailService(EmailServiceInterface):
    @staticmethod
    def send_message(
        To,
        Subject=None,
        Content=None,
    ):
        SENDER = "El Angelito <hi@angelito.baby>"
        RECIPIENT = "bacon_mandala8y@icloud.com"
        AWS_REGION = "US-EAST-2"
        SUBJECT = f"{Subject} Amazon SES Test (SDK for Python)"
        BODY_HTML = f"""
            <html>
                <head></head>
                <body>
                    <h1>Amazon SES Test (SDK for Python)</h1>
                    <p>This email was sent with
                        <a href='https://aws.amazon.com/ses/'>Amazon SES</a> using the
                        <a href='https://aws.amazon.com/sdk-for-python/'>
                        AWS SDK for Python (Boto)</a>.</p>
                    <p>{Content}</p>
                </body>
            </html>
        """
        CHARSET = "UTF-8"

        client = boto3.client('ses',region_name=AWS_REGION)

        try:
            response = client.send_email(
                Destination={ 'ToAddresses': [RECIPIENT] },
                Message={
                    'Body': {
                        'Html': {
                            'Charset': CHARSET,
                            'Data': BODY_HTML,
                        },
                    },
                    'Subject': {
                        'Charset': CHARSET,
                        'Data': SUBJECT,
                    },
                },
                Source=SENDER,
            )
        except ClientError as e:
            print(e.response['Error']['Message'])
        else:
            print("Email sent! Message ID:", response['MessageId'])
            for key in dir(response):
                print(response[key])