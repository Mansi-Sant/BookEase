from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import RoleLoginForm, RoleSignupForm, OTPVerifyForm
from .utils import create_and_send_otp
from .models import OTPRecord

def _role_for(user):
    profile_role = getattr(getattr(user, "role_profile", None), "role", None)
    if user.is_superuser or profile_role == "admin":
        return "admin"
    if profile_role:
        return profile_role
    if user.is_staff:
        return "organizer"
    return "customer"


def _is_admin(user):
    return user.is_authenticated and (
        user.is_superuser
        or getattr(getattr(user, "role_profile", None), "role", None) == "admin"
    )


def login_view(request):
    if request.user.is_authenticated:
        return redirect("role_redirect")

    form = RoleLoginForm(request.POST or None, initial={"role": "customer"})
    if request.method == "POST":
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, "Signed in successfully.")
            return redirect("role_redirect")
        messages.error(request, "Please check your login details.")

    return render(request, "accounts/login.html", {"form": form})


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("role_redirect")

    form = RoleSignupForm(request.POST or None, initial={"role": "customer"})
    if request.method == "POST":
        if form.is_valid():
            email = form.cleaned_data['email'].strip()
            role = form.cleaned_data.get('role', 'customer')

            try:
                create_and_send_otp(email, 'email', role)

                request.session['otp_identifier'] = email
                request.session['otp_method'] = 'email'
                request.session['otp_role'] = role
                request.session['otp_resend_count'] = 0
                request.session['otp_purpose'] = 'signup'
                request.session['pending_signup_data'] = {
                    'full_name': form.cleaned_data.get('full_name', ''),
                    'email': email,
                    'password1': form.cleaned_data.get('password1', ''),
                    'role': role,
                }

                messages.success(request, "OTP sent to your email. Please verify to complete registration.")
                return redirect('otp_verify')

            except Exception as e:
                messages.error(request, str(e) or "Failed to send OTP. Please try again.")
        messages.error(request, "Please fix the highlighted fields.")

    return render(request, "accounts/signup.html", {"form": form})


@login_required
def role_redirect(request):
    role = _role_for(request.user)
    if role == "customer":
        return redirect("/customer/home/")
    if role == "organizer":
        return redirect("/organizer/")
    if role == "admin":
        return redirect("/admin-dashboard/")
    return redirect("/accounts/login/")


@require_POST
def logout_view(request):
    logout(request)
    return redirect("/accounts/login/")


@login_required
@user_passes_test(_is_admin, login_url="/accounts/login/")
@require_POST
def update_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    action = request.POST.get("action")
    if action == "toggle_active" and user != request.user:
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        messages.success(request, "User status updated.")
    elif action == "role":
        role = request.POST.get("role")
        if role in {"customer", "organizer", "admin"} and hasattr(user, "role_profile"):
            user.role_profile.role = role
            user.role_profile.save(update_fields=["role"])
            user.is_staff = role == "admin" or user.is_superuser
            user.save(update_fields=["is_staff"])
            messages.success(request, "User role updated.")
    return redirect("admin_dashboard:user_management")


def _mask_email(email):
    """Helper: mask email for display"""
    if '@' not in email:
        return email
    local, domain = email.split('@', 1)
    prefix = local[:2] if len(local) >= 2 else local[:1]
    return f"{prefix}***@{domain}"


def otp_verify(request):
    otp_identifier = request.session.get('otp_identifier')
    otp_method = request.session.get('otp_method')
    otp_role = request.session.get('otp_role')
    otp_purpose = request.session.get('otp_purpose', 'signup')

    if not otp_identifier or not otp_method or not otp_role:
        messages.error(request, "Session expired. Please try again.")
        return redirect('signup')

    if request.method == 'POST':
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            otp_code = form.cleaned_data['otp_code']
            record = OTPRecord.objects.filter(
                identifier=otp_identifier,
                otp_code=otp_code,
                is_used=False,
                method=otp_method,
                role=otp_role,
            ).order_by('-created_at').first()

            if not record:
                messages.error(request, "Invalid OTP. Please check and try again.")
            elif record.is_expired():
                messages.error(request, "OTP has expired. Please request a new one.")
            else:
                record.is_used = True
                record.save(update_fields=['is_used'])

                pending = request.session.get('pending_signup_data')
                if not pending:
                    messages.error(request, "Signup session expired. Please register again.")
                    return redirect('signup')

                # Parse full name into first and last name
                full_name = pending.get('full_name', '').strip()
                parts = full_name.split(None, 1)

                user = User(
                    username=pending['email'],
                    email=pending['email'],
                    first_name=parts[0] if parts else "",
                    last_name=parts[1] if len(parts) > 1 else "",
                )
                user.set_password(pending['password1'])
                if pending.get('role') == 'organizer':
                    user.is_staff = True
                user.save()

                # Assign role to UserProfile (uses existing signal-created profile)
                if hasattr(user, 'role_profile'):
                    user.role_profile.role = pending.get('role', 'customer')
                    user.role_profile.save()

                login(request, user, backend='django.contrib.auth.backends.ModelBackend')

                for key in ['otp_identifier', 'otp_method', 'otp_role',
                            'otp_resend_count', 'otp_purpose', 'pending_signup_data']:
                    request.session.pop(key, None)

                messages.success(request, "Welcome! Your account has been created successfully.")
                return redirect('role_redirect')
    else:
        form = OTPVerifyForm()

    return render(request, 'accounts/otp_verify.html', {
        'form': form,
        'masked_identifier': _mask_email(otp_identifier),
        'otp_purpose': otp_purpose,
    })


from django.http import JsonResponse


@require_POST
def resend_otp(request):
    otp_identifier = request.session.get('otp_identifier')
    otp_method = request.session.get('otp_method')
    otp_role = request.session.get('otp_role')
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    if not otp_identifier or not otp_method or not otp_role:
        msg = "Session expired. Please try again."
        if is_ajax:
            return JsonResponse({'ok': False, 'message': msg}, status=400)
        messages.error(request, msg)
        return redirect('signup')

    resend_count = int(request.session.get('otp_resend_count', 0))
    if resend_count >= 3:
        msg = "Too many resend attempts. Please try signing up again."
        if is_ajax:
            return JsonResponse({'ok': False, 'message': msg}, status=429)
        messages.error(request, msg)
        return redirect('signup')

    try:
        create_and_send_otp(otp_identifier, otp_method, otp_role)
        request.session['otp_resend_count'] = resend_count + 1
        if is_ajax:
            return JsonResponse({'ok': True, 'message': 'A new OTP has been sent to your email.'})
        messages.success(request, "A new OTP has been sent.")
    except Exception as e:
        msg = str(e) or "Failed to resend OTP. Please try again."
        if is_ajax:
            return JsonResponse({'ok': False, 'message': msg}, status=500)
        messages.error(request, msg)

    return redirect('otp_verify')
