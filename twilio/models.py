import uuid
from django.db import models


class Participant(models.Model):
    """
    Represents an individual user from BCFG, identified by a unique BCFG ID.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bcfg_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    # If you want to tie this to a Django user model for admin/permissions:
    # user = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.bcfg_id})"


class ParticipantGroup(models.Model):
    """
    Represents a group in BCFG with multiple participants.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bcfg_group_id = models.CharField(max_length=255, unique=True)
    # A group can have multiple Participants
    participants = models.ManyToManyField(Participant, related_name='groups')

    # optional additional fields
    school_name = models.CharField(max_length=255, blank=True)
    school_mascot = models.CharField(max_length=255, blank=True)
    initial_message = models.TextField(blank=True)
    week_number = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Group {self.bcfg_group_id}"


class Assistant(models.Model):
    """
    Represents your GPT assistant instance / session info. Could be associated
    to a Participant or a ParticipantGroup.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participant = models.OneToOneField(
        Participant, null=True, blank=True, on_delete=models.CASCADE)
    group = models.OneToOneField(
        ParticipantGroup, null=True, blank=True, on_delete=models.CASCADE)

    # You might store GPT session details, e.g. a conversation ID for the GPT-4 API or
    # some memory tokens, etc.
    gpt_thread_id = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.participant:
            return f"Assistant for Participant {self.participant.name}"
        if self.group:
            return f"Assistant for Group {self.group.bcfg_group_id}"
        return f"Assistant {self.id}"
