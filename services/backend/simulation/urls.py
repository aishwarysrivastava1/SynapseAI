from django.urls import path
from . import views

urlpatterns = [
    path("run", views.SimulationRunView.as_view()),
]
