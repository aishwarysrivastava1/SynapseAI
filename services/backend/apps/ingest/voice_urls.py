from django.urls import path
from . import views

urlpatterns = [
    path("twiml",     views.VoiceTwiMLView.as_view()),
    path("recording", views.VoiceRecordingView.as_view()),
]
