from django.views.generic import TemplateView
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from research.serializers import AskSerializer

from .services import get_research_reponse


class ResearchChatView(TemplateView):
    template_name = "research/chat.html"


class AskAPIView(GenericAPIView):
    serializer_class = AskSerializer

    def post(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        question = serializer.validated_data.get("question")
        response = get_research_reponse(question)

        return Response({"response": response})
