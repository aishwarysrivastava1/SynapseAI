from django.urls import path
from . import views

urlpatterns = [
    path("text",     views.IngestTextView.as_view()),
    path("document", views.IngestDocumentView.as_view()),
    path("voice",    views.IngestVoiceView.as_view()),
]
