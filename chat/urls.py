from django.urls import path
from . import views
app_name = "chat"
urlpatterns = [
    path("", views.chat_page, name="chat_page"),
    path("messages/<str:username>/", views.fetch_messages, name="fetch_messages"),
    path("send/", views.send_message, name="send_message"),
    # path("follow/<str:username>/", views.toggle_follow, name="toggle_follow"),
    path("unread_summary/", views.unread_summary, name="unread_summary"),
]
