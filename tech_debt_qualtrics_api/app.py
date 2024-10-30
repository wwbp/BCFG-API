from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
import logging
from openai import OpenAI

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI client with API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@app.route('/chat', methods=['POST'])
def chat():
    app.logger.debug("Received a request at /chat")
    data = request.get_json()
    app.logger.debug(f"Request data: {data}")
    user_message = data.get('message', '')

    if not user_message:
        app.logger.warning("No message provided in the request")
        return jsonify({'error': 'No message provided'}), 400

    try:
        # Send the user message to OpenAI GPT API using the client
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_message}
            ],
            model="gpt-4o-mini"  # Replace with your desired model
        )

        # Log the OpenAI API request ID
        request_id = response._request_id
        app.logger.debug(f"OpenAI API Request ID: {request_id}")

        # Extract the assistant's reply
        assistant_message = response.choices[0].message.content
        app.logger.debug(f"Assistant's reply: {assistant_message}")

        return jsonify({'reply': assistant_message})
    except Exception as e:
        app.logger.error(f"An error occurred: {e}", exc_info=True)
        return jsonify({'error': 'An error occurred while processing your request.'}), 500


if __name__ == '__main__':
    app.run(debug=True)
