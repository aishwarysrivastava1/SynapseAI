from django.urls import path
from . import views

urlpatterns = [
    path("session", views.GuestSessionView.as_view()),
    path("data",    views.GuestDataView.as_view()),
]
