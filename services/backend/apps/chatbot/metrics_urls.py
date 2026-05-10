from django.urls import path
from . import views

urlpatterns = [
    path("", views.MetricsView.as_view()),
]
