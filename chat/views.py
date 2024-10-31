from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import User, Assistant, Transcript
import json
import logging
import os
import requests
from openai import OpenAI

logging.basicConfig(level=logging.INFO)


class DatabaseInterface:
    def get_user_by_id(self, id):
        raise NotImplementedError

    def create_user(self, name):
        raise NotImplementedError

    def get_or_create_assistant(self, user):
        raise NotImplementedError

    def save_assistant(self, assistant):
        raise NotImplementedError

    def save_transcript(self, user, user_message, assistant_message):
        raise NotImplementedError


class Database(DatabaseInterface):
    def get_user_by_id(self, id):
        try:
            return User.objects.get(id=id)
        except User.DoesNotExist:
            return None

    def create_user(self, name):
        user = User.objects.create(name=name)
        return user

    def get_or_create_assistant(self, user):
        assistant, created = Assistant.objects.get_or_create(user=user)
        return {
            'created': created,
            'user_id': user.id,
            'gpt_assistant_id': assistant.gpt_assistant_id,
            'gpt_thread_id': assistant.gpt_thread_id
        }

    def save_assistant(self, assistant_data):
        assistant = Assistant.objects.get(user_id=assistant_data['user_id'])
        assistant.gpt_assistant_id = assistant_data['gpt_assistant_id']
        assistant.gpt_thread_id = assistant_data['gpt_thread_id']
        assistant.save()

    def save_transcript(self, user, user_message, assistant_message):
        Transcript.objects.create(
            user=user, user_message=user_message, assistant_message=assistant_message)


class ChatService:
    def __init__(self, db: DatabaseInterface, openai_client, requests_lib):
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

    def get_or_create_user(self, context, id):
        if id:
            user = self.db.get_user_by_id(id)
            if user:
                return user
        return self.db.create_user(name=context['name'])

    def initialize_assistant(self, user):
        assistant_data = self.db.get_or_create_assistant(user)
        if assistant_data.get('created'):
            assistant_data['gpt_assistant_id'], assistant_data['gpt_thread_id'] = self.setup_assistant_and_thread(
                user.id)
            self.db.save_assistant(assistant_data)
        return assistant_data

    def setup_assistant_and_thread(self, user_id):
        assistant = self.openai_client.beta.assistants.create(
            name=f"Assistant for user {user_id}",
            instructions="You are a helpful assistant.",
            model="gpt-4o-mini",
        )
        thread = self.openai_client.beta.threads.create()
        return assistant.id, thread.id

    def generate_gpt_response(self, assistant, message):
        self.openai_client.beta.threads.messages.create(
            thread_id=assistant['gpt_thread_id'], role="user", content=message
        )
        run = self.openai_client.beta.threads.runs.create_and_poll(
            thread_id=assistant['gpt_thread_id'], assistant_id=assistant['gpt_assistant_id']
        )
        if run.status == 'completed':
            messages = list(self.openai_client.beta.threads.messages.list(
                thread_id=assistant['gpt_thread_id']))
            return messages[-1].content
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

    def process_message(self, context, message, id):
        user = self.get_or_create_user(context, id)
        assistant = self.initialize_assistant(user)
        gpt_response = self.generate_gpt_response(assistant, message)
        self.db.save_transcript(user, message, gpt_response)
        self.send_message_to_participant(
            user.id, gpt_response)  # Access 'id' as an attribute


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
