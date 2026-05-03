"""
Views load catalog and appointments through the ORM so data always comes from the
configured PostgreSQL database — no mock lists (hackathon "Must Have" / demo integrity).

@login_required is used wherever identity is required (bookings, dashboard, confirmation)
so anonymous users cannot hit appointment URLs or see other users' rows.

Two-step booking: POST containing name="select_slots" filters timeslots by chosen service;
POST containing name="confirm_booking" validates and persists the Appointment, then frees
the slot row locked and marked unavailable in the same transaction as save.
"""

from django.contrib import messages
from django.contrib.auth import login, logout
from django.db import IntegrityError, transaction
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from .forms import (
    AppointmentBookingForm,
    AppointmentFilterForm,
    LoginForm,
    SignupForm,
)
from .models import Appointment, Service, ServiceCategory, TimeSlot
from .utils import (
    build_book_appointment_context,
    get_dashboard_stats,
    get_time_greeting,
)

ITEMS_PER_PAGE = 10


def _pagination_querystring(request):
    q = request.GET.copy()
    q.pop("page", None)
    return q.urlencode()


def _safe_int(value):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _book_get(request):
    sid = _safe_int(request.GET.get("service"))
    form = AppointmentBookingForm(user=request.user, service_id=sid, booking_ui=True)
    ctx = build_book_appointment_context(request, form, sid)
    return render(request, "booking/book_appointment.html", ctx)


def _book_select_slots(request):
    sid = _safe_int(request.POST.get("service"))
    if sid is None:
        messages.error(request, "Please select a valid service.")
        return redirect("book_appointment")
    form = AppointmentBookingForm(
        user=request.user, service_id=sid, data=request.POST, booking_ui=True
    )
    ctx = build_book_appointment_context(request, form, sid)
    return render(request, "booking/book_appointment.html", ctx)


def _book_confirm(request):
    sid = _safe_int(request.POST.get("service"))
    tid_from_post = _safe_int(request.POST.get("timeslot"))
    # If the service hidden input failed to post (rare browser/layout edge cases),
    # derive it from the chosen timeslot so validation and FKs stay consistent.
    if sid is None and tid_from_post is not None:
        sid = (
            TimeSlot.objects.filter(pk=tid_from_post)
            .values_list("service_id", flat=True)
            .first()
        )

    form = AppointmentBookingForm(
        user=request.user, service_id=sid, data=request.POST, booking_ui=True
    )
    ctx = build_book_appointment_context(request, form, sid)
    if not form.is_valid():
        messages.error(request, "Please correct the errors below.")
        return render(request, "booking/book_appointment.html", ctx)

    appointment = form.save(commit=False)
    appointment.user = request.user
    tid = appointment.timeslot_id

    try:
        with transaction.atomic():
            slot = TimeSlot.objects.select_for_update().get(pk=tid)
            if not slot.is_available:
                messages.error(request, "This time slot is no longer available.")
                return render(request, "booking/book_appointment.html", ctx)
            if Appointment.objects.filter(user=request.user, timeslot_id=tid).exists():
                messages.error(
                    request,
                    "You already have an appointment for this time slot.",
                )
                return render(request, "booking/book_appointment.html", ctx)
            slot.is_available = False
            slot.save(update_fields=["is_available"])
            appointment.save()
    except IntegrityError:
        TimeSlot.objects.filter(pk=tid).update(is_available=True)
        messages.error(
            request,
            "Could not complete booking (slot may be taken or you already booked it).",
        )
        return render(request, "booking/book_appointment.html", ctx)

    messages.success(request, "Your appointment has been booked.")
    return redirect("confirmation", reference_code=appointment.reference_code)


@require_http_methods(["GET"])
def home_view(request):
    # ORM hits PostgreSQL; reverse relation is `services` (not Django's default service_set).
    categories_list = (
        ServiceCategory.objects.annotate(
            service_count=Count("services", filter=Q(services__is_active=True))
        ).prefetch_related(
            Prefetch("services", queryset=Service.objects.filter(is_active=True))
        )
    )
    paginator = Paginator(categories_list, ITEMS_PER_PAGE)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    ctx = {
        "categories": page_obj,
        "paginator": paginator,
        "is_paginated": paginator.num_pages > 1,
        "pagination_querystring": _pagination_querystring(request),
        "total_services": Service.objects.filter(is_active=True).count(),
    }
    return render(request, "booking/home.html", ctx)


def signup_view(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created. Welcome to your dashboard.")
            return redirect("dashboard")
    else:
        form = SignupForm()
    return render(request, "booking/signup.html", {"form": form})


def login_view(request):
    next_url = request.POST.get("next") or request.GET.get("next")
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, "Signed in successfully.")
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect("dashboard")
    else:
        form = LoginForm()
    return render(request, "booking/login.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, "You have been signed out.")
    return redirect("home")


@login_required
@require_http_methods(["GET"])
def dashboard_view(request):
    # login_required: appointments must be loaded only for the authenticated user.
    recent_list = (
        Appointment.objects.filter(user=request.user)
        .select_related("service", "timeslot")
        .order_by("-booked_at")
    )
    paginator = Paginator(recent_list, ITEMS_PER_PAGE)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    ctx = {
        "stats": get_dashboard_stats(request.user),
        "recent_appointments": page_obj,
        "paginator": paginator,
        "is_paginated": paginator.num_pages > 1,
        "pagination_querystring": _pagination_querystring(request),
        "user": request.user,
        "greeting": get_time_greeting(),
        "today": timezone.localdate(),
    }
    return render(request, "booking/dashboard.html", ctx)


@require_http_methods(["GET"])
def services_view(request):
    categories_list = ServiceCategory.objects.prefetch_related(
        Prefetch(
            "services",
            queryset=Service.objects.filter(is_active=True),
        )
    )
    paginator = Paginator(categories_list, ITEMS_PER_PAGE)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "booking/services.html",
        {
            "categories": page_obj,
            "paginator": paginator,
            "is_paginated": paginator.num_pages > 1,
            "pagination_querystring": _pagination_querystring(request),
        },
    )


@login_required
def book_appointment_view(request):
    # POST "select_slots" → filter slots; POST "confirm_booking" → validate + save.
    if request.method == "POST" and "select_slots" in request.POST:
        return _book_select_slots(request)
    if request.method == "POST" and "confirm_booking" in request.POST:
        return _book_confirm(request)
    if request.method == "GET":
        return _book_get(request)
    messages.warning(request, "Invalid booking action.")
    return redirect("book_appointment")


@login_required
@require_http_methods(["GET"])
def confirmation_view(request, reference_code):
    appointment = get_object_or_404(
        Appointment.objects.select_related("service", "timeslot"),
        reference_code=reference_code,
        user=request.user,
    )
    return render(
        request,
        "booking/confirmation.html",
        {"appointment": appointment},
    )


@login_required
@require_http_methods(["GET"])
def my_appointments_view(request):
    form = AppointmentFilterForm(request.GET or None)
    appointments = Appointment.objects.filter(user=request.user).select_related(
        "service", "timeslot"
    )
    if form.is_valid():
        st = form.cleaned_data.get("status")
        df = form.cleaned_data.get("date_from")
        dt = form.cleaned_data.get("date_to")
        if st:
            appointments = appointments.filter(status=st)
        if df:
            appointments = appointments.filter(timeslot__date__gte=df)
        if dt:
            appointments = appointments.filter(timeslot__date__lte=dt)
    appointments = appointments.order_by("-booked_at")
    paginator = Paginator(appointments, ITEMS_PER_PAGE)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "booking/my_appointments.html",
        {
            "appointments": page_obj,
            "paginator": paginator,
            "is_paginated": paginator.num_pages > 1,
            "pagination_querystring": _pagination_querystring(request),
            "filter_form": form,
            "today": timezone.localdate(),
        },
    )


@login_required
@require_POST
def cancel_appointment_view(request, appointment_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related("timeslot"),
        id=appointment_id,
        user=request.user,
    )
    if appointment.status != Appointment.STATUS_PENDING:
        messages.error(request, "Only pending appointments can be cancelled.")
        return redirect("my_appointments")
    if appointment.timeslot.date < timezone.localdate():
        messages.error(request, "Cannot cancel appointments in the past.")
        return redirect("my_appointments")
    appointment.status = Appointment.STATUS_CANCELLED
    appointment.save(update_fields=["status"])
    slot = appointment.timeslot
    slot.is_available = True
    slot.save(update_fields=["is_available"])
    messages.success(request, "Appointment cancelled.")
    return redirect("my_appointments")
