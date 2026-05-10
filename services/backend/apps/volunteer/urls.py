from django.urls import path
from . import views

urlpatterns = [
    path("dashboard",                                        views.VolDashboardView.as_view()),
    path("tasks",                                            views.VolTasksView.as_view()),
    path("open-tasks",                                       views.VolOpenTasksView.as_view()),
    path("assignments",                                      views.VolAssignmentsView.as_view()),
    path("assignments/<str:assignment_id>/accept",           views.VolAssignmentActionView.as_view(), kwargs={"action": "accept"}),
    path("assignments/<str:assignment_id>/reject",           views.VolAssignmentActionView.as_view(), kwargs={"action": "reject"}),
    path("assignments/<str:assignment_id>/complete",         views.VolAssignmentActionView.as_view(), kwargs={"action": "complete"}),
    path("tasks/<str:task_id>/enroll",                       views.VolEnrollView.as_view()),
    path("enrollment-requests",                              views.VolEnrollmentRequestsView.as_view()),
    path("recommendations",                                  views.VolRecommendationsView.as_view()),
    path("profile",                                          views.VolProfileView.as_view()),
    path("location",                                         views.VolLocationView.as_view()),
    path("sos",                                              views.VolSOSView.as_view()),
    path("notifications",                                    views.VolNotificationsView.as_view()),
    path("notifications/<str:notif_id>/read",                views.VolNotificationReadView.as_view()),
]
