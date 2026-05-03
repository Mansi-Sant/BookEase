from django.urls import path

from . import views

urlpatterns = [
    path("", views.home_view, name="home"),
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("services/", views.services_view, name="services"),
    path("book/", views.book_appointment_view, name="book_appointment"),
    path(
        "confirmation/<str:reference_code>/",
        views.confirmation_view,
        name="confirmation",
    ),
    path("my-appointments/", views.my_appointments_view, name="my_appointments"),
    path(
        "cancel/<int:appointment_id>/",
        views.cancel_appointment_view,
        name="cancel_appointment",
    ),
]
