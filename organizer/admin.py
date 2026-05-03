from django.contrib import admin

from .models import (
    AppointmentSlot,
    BookingQuestion,
    BookingRule,
    Resource,
    Service,
    WorkingHours,
)


@admin.register(Service)
class OrganizerServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "created_by", "duration_minutes", "appointment_type", "is_published", "created_at")
    list_filter = ("appointment_type", "is_published")
    search_fields = ("name", "description")


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("name", "service", "assigned_user")
    search_fields = ("name", "service__name")


@admin.register(WorkingHours)
class WorkingHoursAdmin(admin.ModelAdmin):
    list_display = ("service", "day_of_week", "start_time", "end_time")


@admin.register(AppointmentSlot)
class AppointmentSlotAdmin(admin.ModelAdmin):
    list_display = ("service", "schedule_type", "date", "day_of_week", "start_time", "end_time", "max_bookings")
    list_filter = ("schedule_type",)
    search_fields = ("service__name",)


@admin.register(BookingQuestion)
class BookingQuestionAdmin(admin.ModelAdmin):
    list_display = ("question_text", "service", "is_required")
    search_fields = ("question_text",)


@admin.register(BookingRule)
class BookingRuleAdmin(admin.ModelAdmin):
    list_display = (
        "service",
        "max_bookings_per_slot",
        "manage_capacity",
        "requires_manual_confirmation",
        "resource_assignment",
    )
