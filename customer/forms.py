from django import forms
from django.contrib.auth.models import User

from organizer.models import AppointmentSlot

from .models import CustomerProfile


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]


class CustomerProfileForm(forms.ModelForm):
    class Meta:
        model = CustomerProfile
        fields = ["phone_number", "date_of_birth", "profile_picture"]


class SlotSelectionForm(forms.Form):
    slot = forms.ModelChoiceField(
        queryset=AppointmentSlot.objects.none(),
        widget=forms.RadioSelect,
    )


class RescheduleForm(forms.Form):
    new_slot = forms.ModelChoiceField(
        queryset=AppointmentSlot.objects.none(),
        widget=forms.RadioSelect,
    )
