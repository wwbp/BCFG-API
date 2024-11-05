from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from .models import User, Assistant, Transcript
import json
import logging
import os
import requests
from openai import OpenAI

logging.basicConfig(level=logging.INFO)


class DatabaseInterface:
    def get_user_by_bcfg_id(self, bcfg_id):
        raise NotImplementedError

    def create_user(self, bcfg_id, name):
        raise NotImplementedError

    def get_or_create_assistant(self, user):
        raise NotImplementedError

    def save_assistant(self, assistant):
        raise NotImplementedError

    def save_transcript(self, user, user_message, assistant_message):
        raise NotImplementedError


class Database(DatabaseInterface):
    def get_user_by_bcfg_id(self, bcfg_id):
        try:
            return User.objects.get(bcfg_id=bcfg_id)
        except User.DoesNotExist:
            return None

    def create_user(self, bcfg_id, name):
        return User.objects.create(bcfg_id=bcfg_id, name=name)

    def get_or_create_assistant(self, user):
        assistant, created = Assistant.objects.get_or_create(user=user)
        return assistant, created

    def save_assistant(self, assistant):
        assistant.save()

    def save_transcript(self, user, user_message, assistant_message):
        Transcript.objects.create(
            user=user, user_message=user_message, assistant_message=assistant_message)


class ChatService:
    def __init__(self, db, openai_client, requests_lib):
        self.db = db
        self.openai_client = openai_client
        self.requests_lib = requests_lib

    def check_required_fields(self, context, message):
        required_fields = ["school_name", "school_mascot",
                           "initial_message", "week_number", "name"]
        missing_fields = [
            field for field in required_fields if field not in context]
        if not message:
            missing_fields.append("message")
        return missing_fields

    def get_or_create_user(self, context, bcfg_id):
        user = self.db.get_user_by_bcfg_id(bcfg_id)
        if user:
            return user
        else:
            return self.db.create_user(bcfg_id=bcfg_id, name=context['name'])

    def initialize_assistant(self, user):
        assistant, created = self.db.get_or_create_assistant(user)
        if created or not assistant.gpt_assistant_id or not assistant.gpt_thread_id:
            assistant.gpt_assistant_id, assistant.gpt_thread_id = self.setup_assistant_and_thread()
            self.db.save_assistant(assistant)
        return assistant

    def setup_assistant_and_thread(self):
        assistant = self.openai_client.beta.assistants.create(
            name=f"Assistant",
            instructions="You are a helpful assistant.",
            model="gpt-4o-mini",
        )
        thread = self.openai_client.beta.threads.create()
        return assistant.id, thread.id

    def generate_gpt_response(self, assistant, message):
        self.openai_client.beta.threads.messages.create(
            thread_id=assistant.gpt_thread_id, role="user", content=message
        )
        run = self.openai_client.beta.threads.runs.create_and_poll(
            thread_id=assistant.gpt_thread_id, assistant_id=assistant.gpt_assistant_id
        )
        if run.status == 'completed':
            messages = list(self.openai_client.beta.threads.messages.list(
                thread_id=assistant.gpt_thread_id))

            logging.info("Sequence of messages in the GPT thread:")
            for msg in messages:
                text_content = ''.join(
                    block.text.value for block in msg.content if block.type == 'text')
                logging.info(f"Role: {msg.role}, Content: {text_content}")

            assistant_messages = [
                msg for msg in messages if msg.role == "assistant"]
            if assistant_messages:
                content_blocks = assistant_messages[0].content
                text = ''.join(
                    block.text.value for block in content_blocks if block.type == 'text')
                return text
            else:
                logging.error("No assistant messages found in the thread.")
                return "There was an error processing your message."
        else:
            logging.error(f"Run failed with status: {run.status}")
            return "There was an error processing your message."

    def send_message_to_participant(self, user_id, gpt_response):
        url = f"http://external-api.com/ai/api/participant/{user_id}/send"
        payload = {"message": gpt_response}
        try:
            response = self.requests_lib.post(url, json=payload)
            self.log_message_receipt(
                user_id, response.status_code, response.text)
        except Exception as e:
            logging.error(
                f"Failed to send GPT response to user {user_id}: {e}")

    def log_message_receipt(self, user_id, status_code, response_text):
        if status_code == 200:
            logging.info(f"Successfully sent GPT response to user {user_id}")
        else:
            logging.warning(f"Failed to send GPT response to user {user_id}: {response_text}")

    def process_message(self, context, message, bcfg_id):
        user = self.get_or_create_user(context, bcfg_id)
        assistant = self.initialize_assistant(user)
        gpt_response = self.generate_gpt_response(assistant, message)
        self.db.save_transcript(user, message, gpt_response)
        self.send_message_to_participant(user.bcfg_id, gpt_response)


@csrf_exempt
def incoming_message(request, id=None):
    if request.method == 'POST':
        data = json.loads(request.body)
        context = data.get('context')
        message = data.get('message')

        service = ChatService(
            db=Database(),
            openai_client=OpenAI(api_key=os.getenv("OPENAI_API_KEY", "")),
            requests_lib=requests
        )

        missing_fields = service.check_required_fields(context, message)
        if missing_fields:
            return JsonResponse({"error": f"Missing fields: {', '.join(missing_fields)}"}, status=400)

        service.process_message(context, message, id)
        return JsonResponse({"status": "received"}, status=200)


# View to render the chat page
def chat_page_view(request):
    return render(request, 'chat/chat_interface.html')

@csrf_exempt  
def chat_send_message(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        message = data.get('message')
        response_message = f"I received your message: {message}"
        return JsonResponse({'response': response_message})
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=400)

def get_conversation(request):
    if request.method == 'GET':
        # For now, we'll return an empty conversation
        return JsonResponse({'conversation': []})
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=400)