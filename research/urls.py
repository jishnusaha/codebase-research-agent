from django.urls import path
from .views import AskAPIView, ResearchChatView

urlpatterns = [
    path("", ResearchChatView.as_view(), name="research-chat"),
    path(
        "ask/",
        AskAPIView.as_view(),
        name="ask-api",
    ),
]
