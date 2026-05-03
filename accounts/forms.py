from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User


class RoleLoginForm(forms.Form):
    ROLE_CHOICES = [
        ("customer", "Customer"),
        ("organizer", "Organizer"),
        ("admin", "Admin"),
    ]

    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    role = forms.ChoiceField(choices=ROLE_CHOICES)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.update(
            {"class": "form-control", "placeholder": "you@example.com"}
        )
        self.fields["password"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Enter password"}
        )
        self.fields["role"].widget.attrs.update({"id": "id_role"})

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email", "").strip()
        password = cleaned_data.get("password")
        selected_role = cleaned_data.get("role")

        if not email or not password or not selected_role:
            return cleaned_data

        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            raise forms.ValidationError("Invalid email or password.")

        user = authenticate(username=user.username, password=password)
        if user is None:
            raise forms.ValidationError("Invalid email or password.")

        if not user.is_active:
            raise forms.ValidationError("This account has been deactivated.")

        profile_role = getattr(getattr(user, "role_profile", None), "role", None)
        is_admin = user.is_superuser or profile_role == "admin"
        if selected_role == "admin":
            if not is_admin:
                raise forms.ValidationError("This account does not have admin access.")
        elif profile_role != selected_role:
            role_label = dict(self.ROLE_CHOICES).get(selected_role, selected_role)
            raise forms.ValidationError(
                f"This account is not registered as a {role_label.lower()}."
            )

        self.user = user
        return cleaned_data

    def get_user(self):
        return getattr(self, "user", None)


class RoleSignupForm(forms.Form):
    ROLE_CHOICES = [
        ("customer", "Customer"),
        ("organizer", "Organizer"),
    ]

    full_name = forms.CharField(max_length=180)
    email = forms.EmailField()
    password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")
    role = forms.ChoiceField(choices=ROLE_CHOICES)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["full_name"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Full name"}
        )
        self.fields["email"].widget.attrs.update(
            {"class": "form-control", "placeholder": "you@example.com"}
        )
        self.fields["password1"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Create password"}
        )
        self.fields["password2"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Confirm password"}
        )
        self.fields["role"].widget.attrs.update({"id": "id_role"})

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and len(password1) < 8:
            self.add_error("password1", "Password must be at least 8 characters.")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Passwords do not match.")
        return cleaned_data

    def save(self):
        full_name = self.cleaned_data["full_name"].strip()
        parts = full_name.split(None, 1)
        email = self.cleaned_data["email"]
        user = User(
            username=email,
            email=email,
            first_name=parts[0] if parts else "",
            last_name=parts[1] if len(parts) > 1 else "",
        )
        user.set_password(self.cleaned_data["password1"])
        user.save()

        if hasattr(user, "role_profile"):
            user.role_profile.role = self.cleaned_data["role"]
            user.role_profile.save(update_fields=["role"])
        return user


class OTPVerifyForm(forms.Form):
    otp_code = forms.CharField(
        max_length=6,
        label="Enter 6-digit OTP",
        widget=forms.TextInput(attrs={
            'maxlength': '6',
            'placeholder': '------',
            'autocomplete': 'one-time-code',
            'inputmode': 'numeric',
            'class': 'form-control otp-single-input',
        })
    )
