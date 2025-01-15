from locust import HttpUser, task, between
import random
import time


class WebsiteUser(HttpUser):
    wait_time = between(1, 2)  # Simulates user think time between actions
    host = "https://bcfgbot.com"  # Base URL for your hosted chatbot

    def on_start(self):
        """
        Simulates a user logging in to the chatbot.
        """
        self.nickname = f"UserTEST{random.randint(1, 1000)}"
        self.user_id = f"UID{random.randint(1, 100000)}"
        self.session_token = None
        self.has_conversed = False  # Track if the user has completed their conversation
        self.login()

    def login(self):
        """
        Simulates user login.
        """
        response = self.client.post(
            "/api/chat/login/",
            json={"nickname": self.nickname, "user_id": self.user_id},
            headers={"Content-Type": "application/json"},
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                self.session_token = self.user_id
                print(f"{self.nickname} logged in successfully.")
            else:
                print(f"{self.nickname} login failed: {data.get('error')}")
        else:
            print(
                f"{self.nickname} login request failed with status: {response.status_code}, Response: {response.text}"
            )

    @task
    def have_conversation(self):
        """
        Simulates a single conversation with the bot and then makes the user idle.
        """
        if self.has_conversed:  # Skip further actions if conversation is already completed
            # Sleep for 60 seconds (or any large number) to simulate idling
            time.sleep(60)
            return

        if not self.session_token:
            print(f"{self.nickname} session token missing. Skipping conversation.")
            return

        for i in range(2):  # Simulate two messages in the conversation
            user_message = f"Test message {i+1} from {self.nickname}"
            response = self.client.post(
                "/api/chat/send/",
                json={"message": user_message},
                headers={
                    "Content-Type": "application/json",
                    "X-User-Id": self.session_token,
                },
            )
            if response.status_code == 200:
                bot_response = response.json().get("response", "No response")
                print(f"{self.nickname} bot response: {bot_response}")
            else:
                print(
                    f"{self.nickname} failed to send message {i+1} with status: {response.status_code}, Response: {response.text}"
                )
            time.sleep(1)  # Pause before sending the next message

        print(f"{self.nickname} has completed the conversation. Going to sleep.")
        self.has_conversed = True  # Mark the user as completed
