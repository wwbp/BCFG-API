# twilio/views.py

import json
import logging
from django.http import JsonResponse
from django.views import View
from django.utils import timezone
from .models import Participant, Assistant
from .sqs_producer import send_to_sqs

logger = logging.getLogger(__name__)


class IndividualMessageView(View):
    """
    Handle POST requests to /api/participant/{id}/incoming
    Payload example:
    {
      "context": {
        "school_name": "...",
        "school_mascot": "...",
        "initial_message": "...",
        "week_number": 4,
        "name": "James"
      },
      "message": "What a lovely day"
    }
    """

    def post(self, request, bcfg_id):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        context = data.get('context', {})
        message = data.get('message')

        if not message:
            return JsonResponse({"error": "Missing 'message' in payload"}, status=400)

        # 1. Retrieve or create Participant
        participant, created = Participant.objects.get_or_create(
            bcfg_id=bcfg_id,
            defaults={
                "name": context.get("name", f"Unknown-{bcfg_id}")
            },
        )
        if not created:
            # Optionally update name if changed in context
            if participant.name != context.get("name"):
                participant.name = context.get("name", participant.name)
                participant.save()

        # 2. Retrieve or create Assistant
        assistant, _ = Assistant.objects.get_or_create(participant=participant)

        # 3. Place a job in SQS to handle GPT processing asynchronously
        sqs_payload = {
            "type": "INDIVIDUAL_MESSAGE",
            "timestamp": str(timezone.now()),
            "participant_id": str(participant.id),
            "assistant_id": str(assistant.id),
            "context": context,
            "message": message,
        }
        send_to_sqs(sqs_payload)

        return JsonResponse({"status": "Created"}, status=201)


class GroupMessageView(View):
    """
    Handle POST requests to /api/participantgroup/{id}/incoming
    Payload example:
    {
      "context": {
        "school_name": "Acme University",
        "school_mascot": "wolverine",
        "initial_message": "Starting college is like [...]",
        "week_number": 4,
        "participants": [
          {"name": "James", "id": "ed720e91-144e-47cf-8eda-ff3d355f3d29"},
          {"name": "Mary",  "id": "97720a92-144e-47cf-8eda-ff3d355f3d29"}
        ]
      },
      "sender_id": "97720a92-144e-47cf-8eda-ff3d355f3d29",
      "message": "What a lovely day"
    }
    """

    def post(self, request, bcfg_group_id):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        context = data.get('context', {})
        sender_id = data.get('sender_id')
        message = data.get('message')

        if not message:
            return JsonResponse({"error": "Missing 'message' in payload"}, status=400)

        # 1. Retrieve or create the group
        group, group_created = ParticipantGroup.objects.get_or_create(
            bcfg_group_id=bcfg_group_id,
            defaults={
                "school_name": context.get("school_name", ""),
                "school_mascot": context.get("school_mascot", ""),
                "initial_message": context.get("initial_message", ""),
                "week_number": context.get("week_number"),
            }
        )
        if not group_created:
            # Optionally update fields if changed
            group.school_name = context.get("school_name", group.school_name)
            group.school_mascot = context.get(
                "school_mascot", group.school_mascot)
            group.initial_message = context.get(
                "initial_message", group.initial_message)
            group.week_number = context.get("week_number", group.week_number)
            group.save()

        # 2. Create or update participants inside the group
        participant_data = context.get('participants', [])
        participant_ids = []
        for pd in participant_data:
            # pd is like {"name": "James", "id": "ed720e91-..."}
            p_obj, _ = Participant.objects.get_or_create(
                bcfg_id=pd["id"],
                defaults={"name": pd["name"]},
            )
            if not group.participants.filter(pk=p_obj.pk).exists():
                group.participants.add(p_obj)
            participant_ids.append(str(p_obj.id))

        # 3. Retrieve or create Assistant for this group
        assistant, _ = Assistant.objects.get_or_create(group=group)

        # 4. Post to SQS for async GPT handling
        sqs_payload = {
            "type": "GROUP_MESSAGE",
            "timestamp": str(timezone.now()),
            "group_id": str(group.id),
            "assistant_id": str(assistant.id),
            "context": context,
            "sender_bcfg_id": sender_id,
            "message": message,
        }
        send_to_sqs(sqs_payload)

        return JsonResponse({"status": "Created"}, status=201)
