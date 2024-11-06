from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('participant/<int:id>/incoming/',
         views.incoming_message, name='incoming_message'),
    path('chat/', views.chat_page_view, name='chat_page'),
    path('chat/send/', views.chat_send_message, name='chat_send_message'),
    path('chat/get_conversation/', views.get_conversation, name='get_conversation'), 
]
