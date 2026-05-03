import logging

from django.conf import settings
from django.core.mail import send_mail

from .models import OTPRecord, generate_otp

logger = logging.getLogger(__name__)


def send_otp_email(email, otp_code):
    """Send OTP via email. Falls back to console print if email not configured."""
    if not settings.DEFAULT_FROM_EMAIL or "your_gmail@gmail.com" in str(
        settings.DEFAULT_FROM_EMAIL
    ):
        print(f"[DEV MODE] OTP for {email}: {otp_code}")
        print("Configure .env with real Gmail credentials to send actual emails.")
        return

    try:
        send_mail(
            subject="Your OTP Verification Code",
            message=(
                f"Your OTP code is: {otp_code}\n"
                "This code is valid for 10 minutes.\n"
                "Do not share this code with anyone."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.exception("Failed to send OTP email to %s", email)
        msg = str(exc)
        if "535" in msg or "Username and Password not accepted" in msg:
            raise Exception(
                "Gmail rejected credentials. Use a Google App Password "
                "(enable 2-Step Verification) and set it in .env."
            ) from exc
        raise Exception("Failed to send OTP email. Please try again.") from exc


def create_and_send_otp(identifier, method, role):
    """Invalidate old OTPs, generate new one, send it."""
    otp_code = generate_otp()

    if method == "email":
        send_otp_email(identifier, otp_code)
    else:
        raise ValueError("Only email OTP is supported at this time.")

    # Invalidate any previous unused OTPs for this identifier
    OTPRecord.objects.filter(identifier=identifier, is_used=False).update(is_used=True)

    # Create new OTP record
    OTPRecord.objects.create(
        identifier=identifier,
        method=method,
        otp_code=otp_code,
        role=role,
    )

    return otp_code

