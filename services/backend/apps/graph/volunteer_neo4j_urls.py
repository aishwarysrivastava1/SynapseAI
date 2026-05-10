from django.urls import path
from . import views

urlpatterns = [
    path("", views.GraphVolunteersView.as_view()),
]
