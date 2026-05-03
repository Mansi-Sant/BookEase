from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Appointment, Service, TimeSlot


class SignupForm(UserCreationForm):
    """Registration with profile fields; all inputs use form-input for CSS hooks."""

    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-input"}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-input"}),
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"class": "form-input"}),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("first_name", "last_name", "email", "username", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("username", "password1", "password2"):
            self.fields[name].widget.attrs.setdefault("class", "form-input float-input")
            self.fields[name].widget.attrs.setdefault("placeholder", " ")
            self.fields[name].required = True
        for name in ("first_name", "last_name", "email"):
            self.fields[name].widget.attrs.setdefault("class", "form-input float-input")
            self.fields[name].widget.attrs.setdefault("placeholder", " ")

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for _fname, field in self.fields.items():
            field.widget.attrs.setdefault("class", "form-input float-input")
            field.widget.attrs.setdefault("placeholder", " ")


class AppointmentBookingForm(forms.ModelForm):
    service = forms.ModelChoiceField(
        queryset=Service.objects.filter(is_active=True),
        widget=forms.Select(attrs={"class": "form-input"}),
    )
    timeslot = forms.ModelChoiceField(
        queryset=TimeSlot.objects.filter(is_available=True),
        widget=forms.Select(attrs={"class": "form-input"}),
    )

    class Meta:
        model = Appointment
        fields = ("service", "timeslot", "notes")
        widgets = {
            "notes": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Any special requests or notes...",
                    "class": "form-input notes-area",
                    "data-notes": "1",
                }
            ),
        }

    def __init__(self, *args, user=None, service_id=None, booking_ui=False, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["service"].queryset = Service.objects.filter(is_active=True)
        today = timezone.localdate()
        ts_qs = TimeSlot.objects.filter(is_available=True, date__gte=today)
        if service_id:
            ts_qs = ts_qs.filter(service_id=service_id)
        self.fields["timeslot"].queryset = ts_qs.order_by("date", "start_time")
        if booking_ui:
            self.fields["service"].widget = forms.HiddenInput()
            self.fields["timeslot"].widget = forms.HiddenInput()
        self.fields["service"].empty_label = None
        self.fields["timeslot"].empty_label = None
        if service_id:
            self.initial.setdefault("service", service_id)

    def clean(self):
        cleaned = super().clean()
        if self.user is None:
            raise ValidationError("You must be signed in to book.")
        service = cleaned.get("service")
        timeslot = cleaned.get("timeslot")
        if not timeslot or not service:
            return cleaned
        if timeslot.service_id != service.id:
            raise ValidationError("Selected time slot does not match the service.")
        today = timezone.localdate()
        if timeslot.date < today:
            raise ValidationError("This time slot is in the past.")
        fresh = TimeSlot.objects.filter(pk=timeslot.pk).first()
        if not fresh or not fresh.is_available:
            raise ValidationError("This time slot is no longer available.")
        if Appointment.objects.filter(user=self.user, timeslot=timeslot).exists():
            raise ValidationError("You already have an appointment for this time slot.")
        return cleaned


class AppointmentFilterForm(forms.Form):
    STATUS_CHOICES = [
        ("", "All"),
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
        ("completed", "Completed"),
    ]
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-input"}),
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-input"}),
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-input"}),
    )
