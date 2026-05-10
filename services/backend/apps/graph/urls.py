from django.urls import path
from . import views

urlpatterns = [
    path("stats",        views.GraphStatsView.as_view()),
    path("needs",        views.GraphNeedsView.as_view()),
    path("volunteers",   views.GraphVolunteersView.as_view()),
    path("tasks",        views.GraphTasksView.as_view()),
    path("hotspots",     views.GraphHotspotsView.as_view()),
    path("causal-chain", views.GraphCausalChainView.as_view()),
    path("ask",          views.GraphAskView.as_view()),
]
