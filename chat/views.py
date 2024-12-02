import random
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseNotAllowed
from .models import Prompt, Activity, UserActivity
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views import View
from django.utils.decorators import method_decorator
import uuid
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


class Database:
    def get_user_by_bcfg_id(self, bcfg_id):
        try:
            return User.objects.get(bcfg_id=str(bcfg_id))
        except User.DoesNotExist:
            return None

    def create_user(self, bcfg_id, name):
        return User.objects.create(bcfg_id=str(bcfg_id), name=name)

    def get_or_create_user(self, bcfg_id, name):
        user = self.get_user_by_bcfg_id(bcfg_id)
        if user:
            return user
        else:
            return self.create_user(bcfg_id, name)

    def get_or_create_assistant(self, user):
        assistant, _ = Assistant.objects.get_or_create(user=user)
        return assistant

    def save_assistant(self, assistant):
        assistant.save()

    def save_transcript(self, user, user_message, assistant_message):
        Transcript.objects.create(
            user=user, user_message=user_message, assistant_message=assistant_message)

    def get_transcripts_for_user(self, user):
        return Transcript.objects.filter(user=user).order_by('created_at')

    def get_prompt_instructions(self, user):
        prompt = Prompt.objects.first()
        activities = UserActivity.objects.filter(
            user=user).select_related('activity')
        instructions = ""
        if prompt:
            instructions += f"Persona:\n{prompt.persona}\n\nKnowledge:\n{prompt.knowledge}\n\n"
        if activities:
            instructions += "Activities:\n"
            for user_activity in activities:
                instructions += f"- {user_activity.activity.content}\n"
        return instructions


class GPTAssistantManager:
    def __init__(self, openai_client):
        self.openai_client = openai_client

    def initialize_assistant(self, assistant, instructions):
        if not assistant.gpt_assistant_id or not assistant.gpt_thread_id:
            assistant.gpt_assistant_id, assistant.gpt_thread_id = self.setup_assistant_and_thread(
                instructions)
            assistant.save()
        return assistant

    def setup_assistant_and_thread(self, instructions):
        assistant = self.openai_client.beta.assistants.create(
            name="Assistant",
            instructions=instructions,
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


class ChatService:
    def __init__(self, db, gpt_manager, requests_lib=None):
        self.db = db
        self.gpt_manager = gpt_manager
        self.requests_lib = requests_lib

    def check_required_fields(self, context, message):
        required_fields = ["school_name", "school_mascot",
                           "initial_message", "week_number", "name"]
        missing_fields = [
            field for field in required_fields if field not in context]
        if not message:
            missing_fields.append("message")
        return missing_fields

    def process_message_for_api(self, context, message, bcfg_id):
        user = self.db.get_or_create_user(bcfg_id, context['name'])
        assistant = self.db.get_or_create_assistant(user)
        instructions = "you are a helpful assistant"
        assistant = self.gpt_manager.initialize_assistant(
            assistant, instructions)
        gpt_response = self.gpt_manager.generate_gpt_response(
            assistant, message)
        self.db.save_transcript(user, message, gpt_response)
        self.send_message_to_participant(user.bcfg_id, gpt_response)

    def process_message_for_chat(self, user_id, message):
        user = self.db.get_user_by_bcfg_id(user_id)
        if not user:
            return {'error': 'User not found. Please log in again.'}
        assistant = self.db.get_or_create_assistant(user)
        instructions = self.db.get_prompt_instructions(user)
        assistant = self.gpt_manager.initialize_assistant(
            assistant, instructions)
        gpt_response = self.gpt_manager.generate_gpt_response(
            assistant, message)
        self.db.save_transcript(user, message, gpt_response)
        return gpt_response

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
            logging.warning(
                f"Failed to send GPT response to user {user_id}: {response_text}")


@csrf_exempt
def prompt_view(request):
    prompt, _ = Prompt.objects.get_or_create(id=1)
    activities = Activity.objects.all()
    if request.method == 'POST':
        prompt.persona = request.POST.get('persona', '')
        prompt.knowledge = request.POST.get('knowledge', '')
        prompt.save()
        return redirect('chat:prompt')
    context = {'prompt': prompt, 'activities': activities}
    return render(request, 'chat/prompt.html', context)


@csrf_exempt
def activity_add(request):
    if request.method == 'POST':
        content = request.POST.get('content', '')
        if content:
            Activity.objects.create(content=content)
        return redirect('chat:prompt')
    else:
        return HttpResponseNotAllowed(['POST'])


@csrf_exempt
def activity_edit(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    if request.method == 'POST':
        content = request.POST.get('content', '')
        activity.content = content
        activity.save()
        return redirect('chat:prompt')
    context = {'activity': activity}
    return render(request, 'chat/activity_edit.html', context)


@csrf_exempt
def activity_delete(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    if request.method == 'POST':
        activity.delete()
        return redirect('chat:prompt')
    else:
        return HttpResponseNotAllowed(['POST'])


@csrf_exempt
def incoming_message(request, id=None):
    if request.method == 'POST':
        data = json.loads(request.body)
        context = data.get('context')
        message = data.get('message')

        db = Database()
        gpt_manager = GPTAssistantManager(
            OpenAI(api_key=os.getenv("OPENAI_API_KEY", "")))
        service = ChatService(
            db=db, gpt_manager=gpt_manager, requests_lib=requests)

        missing_fields = service.check_required_fields(context, message)
        if missing_fields:
            return JsonResponse({"error": f"Missing fields: {', '.join(missing_fields)}"}, status=400)

        service.process_message_for_api(context, message, id)
        return JsonResponse({"status": "received"}, status=200)
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=400)


@xframe_options_exempt
def chat_page_view(request):
    return render(request, 'chat/chat_interface.html')


@csrf_exempt
def chat_send_message(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        message = data.get('message')
        user_id = request.COOKIES.get('chat_user_id')
        if not user_id:
            return JsonResponse({'error': 'User not identified.'}, status=400)

        db = Database()
        gpt_manager = GPTAssistantManager(
            OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        )
        service = ChatService(db=db, gpt_manager=gpt_manager)

        gpt_response = service.process_message_for_chat(user_id, message)
        return JsonResponse({'response': gpt_response})
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=400)


@csrf_exempt
def get_conversation(request):
    if request.method == 'GET':
        # Get chat_user_id from cookie
        chat_user_id = request.COOKIES.get('chat_user_id')
        if not chat_user_id:
            return JsonResponse({'conversation': []})

        db = Database()
        try:
            user = db.get_user_by_bcfg_id(chat_user_id)
            if not user:
                return JsonResponse({'conversation': []})
            transcripts = db.get_transcripts_for_user(user)
            conversation = []

            for transcript in transcripts:
                conversation.append({
                    'content': transcript.user_message,
                    'sender': 'user'
                })
                conversation.append({
                    'content': transcript.assistant_message,
                    'sender': 'bot'
                })

            return JsonResponse({'conversation': conversation})
        except Exception as e:
            logging.error(f"Error fetching conversation: {e}")
            return JsonResponse({'conversation': []})
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=400)


@csrf_exempt
def chat_login(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        nickname = data.get('nickname')
        user_id = data.get('user_id')
        if not nickname or not user_id:
            return JsonResponse({'status': 'error', 'error': 'Nickname and User ID are required.'})
        db = Database()
        user = db.get_or_create_user(user_id, nickname)
        # Assign 3 random activities if not already assigned
        if not UserActivity.objects.filter(user=user).exists():
            activities = list(Activity.objects.all())
            random_activities = random.sample(
                activities, min(3, len(activities)))
            for activity in random_activities:
                UserActivity.objects.create(user=user, activity=activity)
        response = JsonResponse({'status': 'success'})
        response.set_cookie('chat_user_id', user_id,
                            httponly=False, samesite='Lax')
        return response
    else:
        return JsonResponse({'status': 'error', 'error': 'Invalid request method.'})


@csrf_exempt
def get_user_info(request):
    if request.method == 'GET':
        user_id = request.COOKIES.get('chat_user_id')
        if not user_id:
            return JsonResponse({'error': 'User not authenticated'}, status=401)
        db = Database()
        user = db.get_user_by_bcfg_id(user_id)
        if not user:
            return JsonResponse({'error': 'User not found'}, status=404)
        return JsonResponse({'user_id': user.bcfg_id, 'nickname': user.name})
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=400)