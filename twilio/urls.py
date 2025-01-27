from django.urls import path
from .views import IndividualMessageView, GroupMessageView

urlpatterns = [
    path('participant/<str:bcfg_id>/incoming',
         IndividualMessageView.as_view(), name='individual_incoming'),
    path('participantgroup/<str:bcfg_group_id>/incoming',
         GroupMessageView.as_view(), name='group_incoming'),
]
