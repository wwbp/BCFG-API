from django.urls import path
from . import views

urlpatterns = [
    path('participant/<int:id>/incoming/',
         views.incoming_message, name='incoming_message'),
]
