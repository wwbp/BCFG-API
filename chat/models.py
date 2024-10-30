from django.db import models


class User(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Assistant(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    gpt_assistant_id = models.CharField(max_length=100)
    gpt_thread_id = models.CharField(max_length=100)


class Transcript(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    user_message = models.TextField()
    assistant_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
