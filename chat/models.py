from django.db import models


class User(models.Model):
    bcfg_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Assistant(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    gpt_assistant_id = models.CharField(max_length=100)
    gpt_thread_id = models.CharField(max_length=100)
    current_activity_index = models.IntegerField(default=0)
    exchange_count = models.IntegerField(default=0, null=True, blank=True)


class Transcript(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    user_message = models.TextField()
    assistant_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Prompt(models.Model):
    persona = models.TextField()
    knowledge = models.TextField()


class Activity(models.Model):
    content = models.TextField()


class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    activity = models.ForeignKey(Activity, on_delete=models.PROTECT)
