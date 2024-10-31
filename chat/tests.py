from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
from .views import ChatService, DatabaseInterface


class MockDatabase(DatabaseInterface):
    def __init__(self):
        self.users = {}
        self.assistants = {}
        self.transcripts = []

    def get_user_by_id(self, id):
        return self.users.get(id)

    def create_user(self, name):
        user = {"id": len(self.users) + 1, "name": name}
        self.users[user['id']] = user
        return user

    def get_or_create_assistant(self, user):
        if user['id'] in self.assistants:
            return {"created": False, **self.assistants[user['id']]}
        assistant = {
            "user_id": user['id'], "gpt_assistant_id": "assistant_id", "gpt_thread_id": "thread_id"}
        self.assistants[user['id']] = assistant
        return {"created": True, **assistant}

    def save_assistant(self, assistant):
        self.assistants[assistant['user_id']] = assistant

    def save_transcript(self, user, user_message, assistant_message):
        self.transcripts.append({
            "user_id": user['id'],
            "user_message": user_message,
            "assistant_message": assistant_message,
        })


class ChatServiceTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.mock_db = MockDatabase()
        self.mock_openai_client = MagicMock()
        self.mock_requests = MagicMock()  # Mocking requests_lib
        self.service = ChatService(
            db=self.mock_db,
            openai_client=self.mock_openai_client,
            requests_lib=self.mock_requests
        )
        self.incoming_url = reverse('incoming_message', args=[1])

    def test_check_required_fields(self):
        context = {
            "school_name": "Acme University",
            "school_mascot": "wolverine",
            "initial_message": "Starting college is like [...]",
            "name": "James"
        }
        message = "What a lovely day"
        missing_fields = self.service.check_required_fields(context, message)
        self.assertIn("week_number", missing_fields)

    def test_get_or_create_user_creates_new_user(self):
        user = self.service.get_or_create_user({"name": "James"}, None)
        self.assertEqual(user["name"], "James")

    def test_initialize_assistant_creates_new_assistant(self):
        user = self.mock_db.create_user(name="James")
        assistant = self.service.initialize_assistant(user)
        self.assertTrue(assistant.get("created"))

    @patch.object(ChatService, 'generate_gpt_response', return_value="Hello, James!")
    def test_process_message_saves_transcript(self, mock_generate_gpt_response):
        user = self.mock_db.create_user(name="James")
        context = {
            "school_name": "Acme University",
            "school_mascot": "wolverine",
            "initial_message": "Starting college",
            "week_number": 4,
            "name": "James"
        }
        message = "What a lovely day"
        self.service.process_message(context, message, user['id'])
        transcript = self.mock_db.transcripts[0]
        self.assertEqual(transcript["user_message"], message)
        self.assertEqual(transcript["assistant_message"], "Hello, James!")

    def test_send_message_to_participant(self):
        user_id = 1
        gpt_response = "Hello, how can I help you?"

        # Set up the mock for requests_lib.post
        self.mock_requests.post.return_value.status_code = 200
        self.mock_requests.post.return_value.text = "Success"

        # Call the method that should invoke requests_lib.post
        self.service.send_message_to_participant(user_id, gpt_response)

        # Assert requests_lib.post was called correctly
        self.mock_requests.post.assert_called_once_with(
            f"http://external-api.com/ai/api/participant/{user_id}/send",
            json={"message": gpt_response}
        )

    def test_log_message_receipt_success(self):
        with self.assertLogs('root', level='INFO') as log:
            self.service.log_message_receipt(1, 200, "Success")
            self.assertIn(
                "Successfully sent GPT response to user 1", log.output[0])

    def test_log_message_receipt_failure(self):
        with self.assertLogs('root', level='WARNING') as log:
            self.service.log_message_receipt(1, 400, "Error")
            self.assertIn(
                "Failed to send GPT response to user 1", log.output[0])
