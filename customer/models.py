from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from organizer.models import AppointmentSlot, BookingQuestion, Resource, Service


class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="customer_profile")
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.ImageField(upload_to="customer_pics/", blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()} Profile"


@receiver(post_save, sender=User)
def create_customer_profile(sender, instance, created, **kwargs):
    if created:
        CustomerProfile.objects.get_or_create(user=instance)


class Booking(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
        ("rescheduled", "Rescheduled"),
    ]

    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="customer_bookings")
    slot = models.ForeignKey(AppointmentSlot, on_delete=models.CASCADE, related_name="customer_bookings")
    appointment_date = models.DateField(null=True, blank=True)
    party_size = models.PositiveIntegerField(default=1)
    assigned_resource = models.ForeignKey(
        Resource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customer_bookings",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    booked_at = models.DateTimeField(auto_now_add=True)
    reference_code = models.CharField(
        max_length=12,
        unique=True,
        blank=True,
        null=True,
        db_index=True,
        help_text="Human-readable code from username + role prefixes + digits (same scheme as catalog bookings).",
    )
    notes = models.TextField(blank=True, null=True)
    rescheduled_slot = models.ForeignKey(
        AppointmentSlot,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="rescheduled_bookings",
    )

    def __str__(self):
        ref = self.reference_code or "—"
        return f"{ref} — {self.customer.username} -> {self.service.name} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.reference_code:
            from booking.utils import generate_portal_reference_code

            self.reference_code = generate_portal_reference_code(
                self.customer,
                exclude_booking_pk=self.pk,
            )
        super().save(*args, **kwargs)

    @property
    def display_date(self):
        return self.appointment_date or self.slot.date


class BookingAnswer(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(BookingQuestion, on_delete=models.CASCADE)
    answer_text = models.TextField()

    def __str__(self):
        return f"Answer for booking #{self.booking.id}"
