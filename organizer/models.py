import uuid

from django.contrib.auth.models import User
from django.db import models


class Service(models.Model):
    APPOINTMENT_TYPE_CHOICES = [
        ("one_to_one", "One-to-One"),
        ("group", "Group"),
        ("resource", "Resource-based"),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField()
    duration_minutes = models.IntegerField()
    appointment_type = models.CharField(
        max_length=20,
        choices=APPOINTMENT_TYPE_CHOICES,
        default="one_to_one",
    )
    venue = models.CharField(max_length=255, blank=True)
    is_published = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="services")
    created_at = models.DateTimeField(auto_now_add=True)
    share_token = models.UUIDField(default=uuid.uuid4, unique=True)

    def __str__(self):
        return self.name


class Resource(models.Model):
    name = models.CharField(max_length=200)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="resources")
    assigned_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_resources",
    )

    def __str__(self):
        return f"{self.name} ({self.service.name})"


class WorkingHours(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="working_hours")
    day_of_week = models.IntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.service.name} - Day {self.day_of_week}"


class AppointmentSlot(models.Model):
    SCHEDULE_WEEKLY = "weekly"
    SCHEDULE_FLEXIBLE = "flexible"
    SCHEDULE_CHOICES = [
        (SCHEDULE_WEEKLY, "Weekly"),
        (SCHEDULE_FLEXIBLE, "Flexible"),
    ]

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="slots")
    schedule_type = models.CharField(max_length=20, choices=SCHEDULE_CHOICES)
    day_of_week = models.IntegerField(null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    max_bookings = models.IntegerField(default=1)
    resource = models.ForeignKey(
        Resource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointment_slots",
    )

    def __str__(self):
        day = self.date or f"weekday {self.day_of_week}"
        return f"{self.service.name} {day} {self.start_time}-{self.end_time}"

    def label(self):
        if self.schedule_type == self.SCHEDULE_WEEKLY:
            names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            day = names[self.day_of_week] if self.day_of_week is not None else "Weekly"
            return f"{day} {self.start_time:%H:%M}-{self.end_time:%H:%M}"
        return f"{self.date} {self.start_time:%H:%M}-{self.end_time:%H:%M}"


class BookingQuestion(models.Model):
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="booking_questions"
    )
    question_text = models.CharField(max_length=255)
    is_required = models.BooleanField(default=False)

    def __str__(self):
        return self.question_text


class BookingRule(models.Model):
    ASSIGNMENT_AUTO = "auto"
    ASSIGNMENT_MANUAL = "manual"
    RESOURCE_ASSIGNMENT_CHOICES = [
        (ASSIGNMENT_AUTO, "Auto"),
        (ASSIGNMENT_MANUAL, "Manual"),
    ]

    service = models.OneToOneField(
        Service, on_delete=models.CASCADE, related_name="booking_rule"
    )
    max_bookings_per_slot = models.IntegerField(default=1)
    manage_capacity = models.BooleanField(default=True)
    advance_payment_enabled = models.BooleanField(default=False)
    requires_manual_confirmation = models.BooleanField(default=False)
    resource_assignment = models.CharField(
        max_length=10,
        choices=RESOURCE_ASSIGNMENT_CHOICES,
        default=ASSIGNMENT_AUTO,
    )

    def __str__(self):
        return f"Rules for {self.service.name}"
