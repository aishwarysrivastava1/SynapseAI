from django.urls import path
from . import views

urlpatterns = [
    path("signup",                views.SignupView.as_view(),             name="auth-signup"),
    path("login",                 views.LoginView.as_view(),              name="auth-login"),
    path("google",                views.GoogleAuthView.as_view(),         name="auth-google"),
    path("guest",                 views.GuestLoginView.as_view(),         name="auth-guest"),
    path("guest-volunteer",       views.GuestVolunteerLoginView.as_view(),name="auth-guest-volunteer"),
    path("ngo/create",            views.NGOCreateView.as_view(),          name="auth-ngo-create"),
    path("check-email",           views.CheckEmailView.as_view(),         name="auth-check-email"),
    path("logout",                views.LogoutView.as_view(),             name="auth-logout"),
    path("ngo/lookup/<str:invite_code>", views.NGOLookupView.as_view(),  name="auth-ngo-lookup"),
]
