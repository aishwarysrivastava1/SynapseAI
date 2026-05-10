from django.urls import path
from . import views

urlpatterns = [
    path("", views.SeedView.as_view()),
]
