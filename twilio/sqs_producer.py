import os
import json
import boto3
import logging

logger = logging.getLogger(__name__)

# e.g. from environment variable
SQS_QUEUE_URL = os.environ.get('SQS_QUEUE_URL', '')

sqs_client = boto3.client(
    'sqs', region_name=os.environ.get('AWS_REGION', 'us-east-1'))


def send_to_sqs(payload: dict) -> None:
    """
    Sends a JSON payload to the configured SQS queue.
    """
    if not SQS_QUEUE_URL:
        logger.error("No SQS_QUEUE_URL configured.")
        return
    try:
        response = sqs_client.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(payload)
        )
        logger.info(f"Sent message to SQS. MessageId={response['MessageId']}")
    except Exception as e:
        logger.exception("Failed to send message to SQS: %s", e)
        raise
