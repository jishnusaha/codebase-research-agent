from django.urls import path
from .views import AskAPIView

urlpatterns = [
    path(
        "ask/",
        AskAPIView.as_view(),
        name="ask-api",
    ),
]
