from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

import random
import string
from datetime import timedelta


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ("customer", "Customer"),
        ("organizer", "Organizer"),
        ("admin", "Admin"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="role_profile",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="customer")
    phone_number = models.CharField(max_length=15, blank=True, null=True, unique=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class OTPRecord(models.Model):
    METHOD_CHOICES = [
        ("email", "Email"),
        ("phone", "Phone"),
    ]

    identifier = models.CharField(max_length=255)  # stores email or phone number
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    otp_code = models.CharField(max_length=6)
    role = models.CharField(max_length=20, default="customer")  # selected role
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)

    def __str__(self):
        return (
            f"{self.identifier} - {self.otp_code} "
            f"({'used' if self.is_used else 'active'})"
        )


def generate_otp():
    return "".join(random.choices(string.digits, k=6))


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
