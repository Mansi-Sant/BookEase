from django.contrib import admin

from .models import Booking, BookingAnswer, CustomerProfile


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone_number", "date_of_birth", "created_at")
    search_fields = ("user__username", "user__email", "phone_number")


@admin.register(Booking)
class CustomerBookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "reference_code",
        "customer",
        "service",
        "slot",
        "status",
        "appointment_date",
        "party_size",
        "booked_at",
    )
    list_filter = ("status",)
    search_fields = ("reference_code", "customer__username", "notes")


@admin.register(BookingAnswer)
class BookingAnswerAdmin(admin.ModelAdmin):
    list_display = ("booking", "question")
    search_fields = ("answer_text", "question__question_text")
