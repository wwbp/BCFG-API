# lambda_function.py - AWS Lambda code snippet
import json
import os
import logging
import requests  # If you want to call external endpoints
import openai    # Example GPT usage, if you are using OpenAI

logger = logging.getLogger()
logger.setLevel(logging.INFO)

BCFG_INDIVIDUAL_SEND_URL = os.environ.get("BCFG_INDIVIDUAL_SEND_URL", "")
BCFG_GROUP_SEND_URL = os.environ.get("BCFG_GROUP_SEND_URL", "")

openai.api_key = os.environ.get("OPENAI_API_KEY", "")


def generate_gpt_response(context, message):
    """
    Example GPT call using the OpenAI API.
    Return a string with the AI's response.
    """
    prompt = f"Context: {json.dumps(context)}\nUser: {message}\nAssistant:"
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": prompt}],
        # additional parameters as needed
    )
    return response['choices'][0]['message']['content']


def lambda_handler(event, context):
    """
    Main entry point for Lambda. event contains SQS messages.
    """
    records = event.get('Records', [])
    for record in records:
        sqs_body = record['body']
        try:
            data = json.loads(sqs_body)
            msg_type = data.get("type")
            # e.g. 'INDIVIDUAL_MESSAGE' or 'GROUP_MESSAGE'
            user_message = data.get("message")
            bcfg_context = data.get("context", {})

            # Step 1: Decide if we want to respond.
            #   For example, you could have logic that says "only respond if X conditions are met".
            #   For now, we assume we always want to respond.

            # Step 2: Generate GPT response
            gpt_response = generate_gpt_response(bcfg_context, user_message)
            logger.info(f"GPT response: {gpt_response}")

            # Step 3: Send response back to BCFG
            if msg_type == "INDIVIDUAL_MESSAGE":
                # We can get the participant's BCFG ID if we had stored it
                # or just store it in the SQS payload.
                # For demonstration, let's assume we have participant_bcfg_id in the context or data.
                # In your real code, you might also store that in the sqs payload so it's direct.
                # Suppose you do:
                #   data["bcfg_id"] = <something>
                # Then you'd do:
                participant_bcfg_id = bcfg_context.get("bcfg_id")
                # Or you might have it from your Django model if you query the DB from Lambda.

                if not participant_bcfg_id:
                    logger.warning(
                        "No participant BCFG ID found, skipping send.")
                    continue

                payload = {"message": gpt_response}
                send_url = f"{BCFG_INDIVIDUAL_SEND_URL}/{participant_bcfg_id}/send"
                # Example: "https://some-bcfg-host/ai/api/participant/{participant_bcfg_id}/send"

                logger.info(f"Sending GPT response to {send_url}")
                res = requests.post(send_url, json=payload)
                logger.info(f"BCFG response status: {res.status_code}")

            elif msg_type == "GROUP_MESSAGE":
                group_bcfg_id = bcfg_context.get("bcfg_group_id")
                if not group_bcfg_id:
                    logger.warning("No group BCFG ID found, skipping send.")
                    continue

                payload = {"message": gpt_response}
                send_url = f"{BCFG_GROUP_SEND_URL}/{group_bcfg_id}/send"
                # Example: "https://some-bcfg-host/ai/api/participantgroup/{group_bcfg_id}/send"

                logger.info(f"Sending GPT response to {send_url}")
                res = requests.post(send_url, json=payload)
                logger.info(f"BCFG response status: {res.status_code}")

        except Exception as e:
            logger.exception("Error processing SQS message: %s", e)

    return {"statusCode": 200}
