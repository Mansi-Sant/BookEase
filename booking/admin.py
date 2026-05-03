from django.contrib import admin

from .models import Appointment, Service, ServiceCategory, TimeSlot, UserProfile


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "icon_emoji")
    search_fields = ("name",)


@admin.register(Service)
class BookingServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "duration_minutes", "price", "is_active")
    list_filter = ("is_active", "category")
    search_fields = ("name", "description")


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ("service", "date", "start_time", "end_time", "is_available", "max_capacity")
    list_filter = ("date", "is_available")
    search_fields = ("service__name",)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("reference_code", "user", "service", "timeslot", "status", "booked_at")
    list_filter = ("status",)
    search_fields = ("reference_code", "user__username", "notes")


@admin.register(UserProfile)
class BookingUserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone")
    search_fields = ("user__username", "phone")
