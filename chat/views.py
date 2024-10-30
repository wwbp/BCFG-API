from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import User, Assistant, Transcript
import json
import threading
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

@csrf_exempt
def incoming_message(request, id=None):
    if request.method == 'POST':
        data = json.loads(request.body)
        context = data.get('context')
        message = data.get('message')

        # Async processing
        def process_message(context, message, id):
            try:
                logging.info(f"Processing message for user with id: {id}")
                if id is None:
                    # Create a new user
                    user = User.objects.create(name=context['name'])
                    logging.info(f"Created new user: {user.name}")
                    Assistant.objects.create(user=user, gpt_assistant_id="assistant_id", gpt_thread_id="thread_id")
                else:
                    # Fetch existing user or handle if not found
                    try:
                        user = User.objects.get(id=id)
                        logging.info(f"Found existing user: {user.name}")
                    except User.DoesNotExist:
                        # Handle case where the user ID doesn't exist
                        logging.warning(f"User with id {id} does not exist. Creating new user.")
                        user = User.objects.create(name=context['name'])
                        Assistant.objects.create(user=user, gpt_assistant_id="assistant_id", gpt_thread_id="thread_id")
                    
                # Create a transcript entry
                Transcript.objects.create(user=user, user_message=message)
                logging.info(f"Transcript created with message: {message}")
            except Exception as e:
                logging.error(f"Error processing message: {e}")

        # Start async processing in a new thread
        thread = threading.Thread(target=process_message, args=(context, message, id))
        thread.start()

        return JsonResponse({"status": "received"}, status=200)
