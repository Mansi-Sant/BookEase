import random
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone

from .models import Appointment, Service, TimeSlot


def get_user_role(user):
    """
    Role string for reference-code generation, aligned with this project's role system
    (accounts.UserProfile via user.role_profile: customer / organizer / admin).
    """
    profile_role = getattr(getattr(user, "role_profile", None), "role", None)
    if user.is_superuser or profile_role == "admin":
        return "admin"
    if profile_role:
        return profile_role
    if user.is_staff:
        return "organizer"
    return "customer"


def _username_for_reference(user):
    if not user:
        return ""
    if hasattr(user, "get_username"):
        return user.get_username() or ""
    return str(getattr(user, "username", "") or "")


def _segment_prefix(segment):
    """
    Build username or role prefix: 1–2 uppercase chars; empty → 'XX';
    one character → that character only, uppercased; otherwise first two chars uppercased
    (e.g. 'user_type_1' → 'US').
    """
    if segment is None:
        return "XX"
    s = str(segment).strip()
    if not s:
        return "XX"
    if len(s) == 1:
        return s[0].upper()
    return s[:2].upper()


def _reference_code_available(
    code,
    exclude_appointment_pk=None,
    exclude_booking_pk=None,
):
    """Ensure codes never collide between booking.Appointment and customer.Booking."""
    qs_a = Appointment.objects.filter(reference_code=code)
    if exclude_appointment_pk is not None:
        qs_a = qs_a.exclude(pk=exclude_appointment_pk)
    if qs_a.exists():
        return False
    try:
        from customer.models import Booking as PortalBooking
    except ImportError:
        return True
    qs_b = PortalBooking.objects.filter(reference_code=code)
    if exclude_booking_pk is not None:
        qs_b = qs_b.exclude(pk=exclude_booking_pk)
    return not qs_b.exists()


def generate_reference_code(user, exclude_appointment_pk=None):
    """
    Unique reference: [username prefix] + [role prefix] + [3 random digits].
    Username prefix from user.get_username(); role from get_user_role(user).
    """
    username_prefix = _segment_prefix(_username_for_reference(user))
    role_prefix = _segment_prefix(get_user_role(user))

    for _attempts in range(100):
        digits = str(random.randint(0, 999)).zfill(3)
        reference_code = f"{username_prefix}{role_prefix}{digits}"
        if _reference_code_available(
            reference_code,
            exclude_appointment_pk=exclude_appointment_pk,
        ):
            return reference_code

    raise ValueError("Could not generate a unique reference code after 100 attempts.")


def generate_portal_reference_code(user, exclude_booking_pk=None):
    """
    Same format as catalog appointments; reserved unique across portal + catalog tables.
    """
    username_prefix = _segment_prefix(_username_for_reference(user))
    role_prefix = _segment_prefix(get_user_role(user))

    for _attempts in range(100):
        digits = str(random.randint(0, 999)).zfill(3)
        reference_code = f"{username_prefix}{role_prefix}{digits}"
        if _reference_code_available(
            reference_code,
            exclude_booking_pk=exclude_booking_pk,
        ):
            return reference_code

    raise ValueError("Could not generate a unique portal reference code after 100 attempts.")


def _appointment_slot_start(appointment):
    naive = datetime.combine(appointment.timeslot.date, appointment.timeslot.start_time)
    if settings.USE_TZ:
        return timezone.make_aware(naive, timezone.get_current_timezone())
    return naive


def get_dashboard_stats(user):
    """Aggregate counts for the dashboard cards."""
    qs = Appointment.objects.filter(user=user).select_related("timeslot")
    total = qs.count()
    cancelled = qs.filter(status=Appointment.STATUS_CANCELLED).count()
    completed = qs.filter(status=Appointment.STATUS_COMPLETED).count()
    now = timezone.now()
    upcoming = 0
    for ap in qs.filter(
        status__in=(Appointment.STATUS_PENDING, Appointment.STATUS_CONFIRMED)
    ):
        if _appointment_slot_start(ap) >= now:
            upcoming += 1
    return {
        "total": total,
        "upcoming": upcoming,
        "cancelled": cancelled,
        "completed": completed,
    }


def mark_timeslot_unavailable(timeslot_id):
    """Reserve slot in DB after a booking is placed (Odoo-style availability)."""
    TimeSlot.objects.filter(pk=timeslot_id).update(is_available=False)


def get_time_greeting():
    """Dashboard salutation by local hour (Odoo portal-style welcome line)."""
    h = timezone.localtime().hour
    if h < 12:
        return "Good morning"
    if h < 17:
        return "Good afternoon"
    return "Good evening"


def get_services_for_booking():
    """Active catalog from PostgreSQL for the booking wizard (no mock rows)."""
    return (
        Service.objects.filter(is_active=True)
        .select_related("category")
        .order_by("category__name", "name")
    )


def get_slot_rows_for_service(service_id, user):
    """
    Build slot rows for the pill grid: includes taken slots (greyed) so the UI matches
    real availability from the DB while the form queryset stays strict for validation.
    """
    if not service_id:
        return []
    today = timezone.localdate()
    qs = (
        TimeSlot.objects.filter(service_id=service_id, date__gte=today)
        .select_related("service", "service__category")
        .order_by("date", "start_time")
    )
    user_slots = set(
        Appointment.objects.filter(user=user).values_list("timeslot_id", flat=True)
    )
    rows = []
    for slot in qs:
        blocked_user = slot.pk in user_slots
        selectable = slot.is_available and not blocked_user
        reason = ""
        if blocked_user:
            reason = "You already booked this slot"
        elif not slot.is_available:
            reason = "Booked"
        rows.append(
            {
                "slot": slot,
                "selectable": selectable,
                "disabled_label": reason,
            }
        )
    return rows


def build_booking_calendar_weeks(slot_rows, weeks_forward=6):
    """
    Calendar grid (Monday-start weeks) for the booking UI.

    Each day cell state:
      past    — before today (neutral styling)
      open    — at least one selectable timeslot (green)
      closed  — no slots, or only booked / blocked slots (red)
    """
    today = timezone.localdate()
    start = today - timedelta(days=today.weekday())  # Monday of current week
    end = today + timedelta(weeks=weeks_forward)
    if slot_rows:
        last_slot_date = max(row["slot"].date for row in slot_rows)
        end = max(end, last_slot_date)

    has_open = {}
    for row in slot_rows:
        iso = row["slot"].date.isoformat()
        if iso not in has_open:
            has_open[iso] = False
        if row["selectable"]:
            has_open[iso] = True

    weeks = []
    cur = start
    while cur <= end:
        week = []
        for _ in range(7):
            iso = cur.isoformat()
            if cur < today:
                state = "past"
            elif iso in has_open:
                state = "open" if has_open[iso] else "closed"
            else:
                state = "closed"
            week.append(
                {
                    "date": cur,
                    "iso": iso,
                    "day_num": cur.day,
                    "weekday": cur.weekday(),
                    "state": state,
                }
            )
            cur += timedelta(days=1)
        weeks.append(week)
    return weeks


def apply_selectable_timeslots_to_form(form, slot_rows):
    """Narrow ModelChoiceField queryset to slots the user may actually POST (prevents spoofing)."""
    if not slot_rows:
        return
    ids = [row["slot"].pk for row in slot_rows if row["selectable"]]
    if ids:
        form.fields["timeslot"].queryset = TimeSlot.objects.filter(pk__in=ids).order_by(
            "date", "start_time"
        )
    else:
        form.fields["timeslot"].queryset = TimeSlot.objects.none()


def build_book_appointment_context(request, form, selected_service_id):
    """Shared template context for GET / select_slots / invalid confirm (keeps views short)."""
    services_for_booking = get_services_for_booking()
    slot_rows = (
        get_slot_rows_for_service(selected_service_id, request.user)
        if selected_service_id
        else []
    )
    apply_selectable_timeslots_to_form(form, slot_rows)
    calendar_weeks = (
        build_booking_calendar_weeks(slot_rows if slot_rows is not None else [])
        if selected_service_id
        else []
    )
    return {
        "form": form,
        "services_for_booking": services_for_booking,
        "selected_service_id": selected_service_id,
        "slot_rows": slot_rows,
        "calendar_weeks": calendar_weeks,
    }
