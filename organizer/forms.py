from django import forms
from django.contrib.auth.models import User

from .models import (
    AppointmentSlot,
    BookingQuestion,
    BookingRule,
    Resource,
    Service,
    WorkingHours,
)


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ["name", "description", "duration_minutes", "venue"]


class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = ["name", "assigned_user"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_user"].queryset = User.objects.all().order_by("username")


class WorkingHoursForm(forms.ModelForm):
    class Meta:
        model = WorkingHours
        fields = ["day_of_week", "start_time", "end_time"]


class AppointmentSlotForm(forms.ModelForm):
    class Meta:
        model = AppointmentSlot
        fields = [
            "schedule_type",
            "day_of_week",
            "date",
            "start_time",
            "end_time",
            "max_bookings",
            "resource",
        ]

    def __init__(self, *args, **kwargs):
        service = kwargs.pop("service", None)
        super().__init__(*args, **kwargs)
        self.fields["day_of_week"].widget = forms.Select(
            choices=[
                ("", "Select weekday"),
                (0, "Monday"),
                (1, "Tuesday"),
                (2, "Wednesday"),
                (3, "Thursday"),
                (4, "Friday"),
                (5, "Saturday"),
                (6, "Sunday"),
            ]
        )
        if service is not None:
            self.fields["resource"].queryset = service.resources.all()

    def clean(self):
        cleaned_data = super().clean()
        schedule_type = cleaned_data.get("schedule_type")
        day_of_week = cleaned_data.get("day_of_week")
        date = cleaned_data.get("date")
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        if schedule_type == AppointmentSlot.SCHEDULE_WEEKLY and day_of_week is None:
            self.add_error("day_of_week", "Choose a weekday for weekly slots.")
        if schedule_type == AppointmentSlot.SCHEDULE_FLEXIBLE and not date:
            self.add_error("date", "Choose a date for flexible slots.")
        if start_time and end_time and end_time <= start_time:
            self.add_error("end_time", "End time must be after start time.")
        return cleaned_data


class BookingQuestionForm(forms.ModelForm):
    class Meta:
        model = BookingQuestion
        fields = ["question_text", "is_required"]


class BookingRuleForm(forms.ModelForm):
    class Meta:
        model = BookingRule
        fields = [
            "max_bookings_per_slot",
            "manage_capacity",
            "advance_payment_enabled",
            "requires_manual_confirmation",
            "resource_assignment",
        ]


class AppointmentTypeForm(forms.Form):
    TYPE_CHOICES = [
        ("one_to_one", "One-to-One (single customer per slot)"),
        ("group", "Group (multiple customers per slot)"),
        ("resource", "Resource-based (assign a resource per booking)"),
    ]
    appointment_type = forms.ChoiceField(
        choices=TYPE_CHOICES,
        widget=forms.RadioSelect,
        label="Appointment Type",
    )
