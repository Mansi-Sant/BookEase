from django.contrib import admin

from .models import OTPRecord, UserProfile


@admin.register(UserProfile)
class AccountsUserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "phone_number")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email", "phone_number")


@admin.register(OTPRecord)
class OTPRecordAdmin(admin.ModelAdmin):
    list_display = ("identifier", "method", "role", "otp_code", "is_used", "created_at")
    list_filter = ("method", "is_used", "role")
    search_fields = ("identifier", "otp_code")
