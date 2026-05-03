from django.urls import path

from . import views

app_name = "admin_dashboard"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("users/", views.user_management, name="user_management"),
    path("services/", views.services, name="services"),
    path("bookings/", views.bookings, name="bookings"),
]
