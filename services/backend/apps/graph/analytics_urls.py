from django.urls import path
from . import views

urlpatterns = [
    # PostgreSQL-backed
    path("ngo-overview",         views.NGOOverviewView.as_view()),
    path("skill-gaps",           views.SkillGapsView.as_view()),
    path("leaderboard",          views.LeaderboardView.as_view()),
    # Neo4j graph analytics
    path("summary",              views.AnalyticsSummaryView.as_view()),
    path("needs-by-type",        views.AnalyticsNeedsByTypeView.as_view()),
    path("urgency-distribution", views.UrgencyDistributionView.as_view()),
    path("skill-coverage",       views.SkillCoverageView.as_view()),
    path("hotzone-ranking",      views.HotzoneRankingView.as_view()),
    path("volunteer-activity",   views.VolunteerActivityView.as_view()),
    # Firebase analytics
    path("trend",                views.TrendView.as_view()),
    path("coverage-history",     views.CoverageHistoryView.as_view()),
]
