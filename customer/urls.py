from django.urls import path

from . import views

urlpatterns = [
    path("home/", views.home, name="customer_home"),
    path("services/", views.service_list, name="customer_service_list"),
    path("services/<int:service_id>/", views.service_detail, name="customer_service_detail"),
    path("services/<int:service_id>/book/", views.book_service, name="book_service"),
    path("bookings/", views.my_bookings, name="my_bookings"),
    path("bookings/<int:booking_id>/", views.booking_detail, name="booking_detail"),
    path(
        "bookings/<int:booking_id>/confirmation/",
        views.booking_confirmation,
        name="booking_confirmation",
    ),
    path("bookings/<int:booking_id>/cancel/", views.cancel_booking, name="cancel_booking"),
    path(
        "bookings/<int:booking_id>/reschedule/",
        views.reschedule_booking,
        name="reschedule_booking",
    ),
    path("profile/", views.profile, name="customer_profile"),
]
