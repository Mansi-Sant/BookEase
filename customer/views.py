from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from datetime import datetime

from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from organizer.models import (
    AppointmentSlot,
    BookingQuestion,
    BookingRule,
    Resource,
    Service,
    WorkingHours,
)

from .forms import CustomerProfileForm, RescheduleForm, SlotSelectionForm, UserUpdateForm
from .models import Booking, BookingAnswer, CustomerProfile

ITEMS_PER_PAGE = 10


def _pagination_querystring(request):
    q = request.GET.copy()
    q.pop("page", None)
    return q.urlencode()


def _parse_date(value):
    if not value:
        return timezone.localdate()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return timezone.localdate()


def _matching_slots(service, selected_date):
    weekday = selected_date.weekday()
    return AppointmentSlot.objects.filter(service=service).filter(
        Q(schedule_type=AppointmentSlot.SCHEDULE_FLEXIBLE, date=selected_date)
        | Q(schedule_type=AppointmentSlot.SCHEDULE_WEEKLY, day_of_week=weekday)
        | Q(schedule_type=AppointmentSlot.SCHEDULE_WEEKLY, day_of_week__isnull=True)
    )


def _used_capacity(slot, appointment_date):
    return (
        Booking.objects.filter(slot=slot, appointment_date=appointment_date)
        .exclude(status="cancelled")
        .aggregate(total=Sum("party_size"))["total"]
        or 0
    )


def _spots_left(slot, appointment_date):
    return max(0, slot.max_bookings - _used_capacity(slot, appointment_date))


def _available_slot_rows(service, selected_date):
    rows = []
    for slot in _matching_slots(service, selected_date).select_related("resource"):
        left = _spots_left(slot, selected_date)
        if left > 0:
            rows.append({"slot": slot, "spots_left": left})
    return rows


@login_required
def home(request):
    featured_services_list = (
        Service.objects.filter(is_published=True)
        .select_related("created_by")
        .order_by("-created_at")
    )
    total_services = Service.objects.filter(is_published=True).count()
    upcoming_bookings_list = (
        Booking.objects.filter(customer=request.user, status__in=["pending", "confirmed"])
        .select_related("service", "slot", "service__created_by")
        .order_by("slot__start_time")
    )
    services_this_week = featured_services_list[:6].count()
    page_number = request.GET.get("page", 1)
    paginator_featured = Paginator(featured_services_list, ITEMS_PER_PAGE)
    paginator_upcoming = Paginator(upcoming_bookings_list, ITEMS_PER_PAGE)
    featured_services = paginator_featured.get_page(page_number)
    upcoming_bookings = paginator_upcoming.get_page(page_number)
    return render(
        request,
        "customer/home.html",
        {
            "featured_services": featured_services,
            "total_services": total_services,
            "upcoming_bookings": upcoming_bookings,
            "services_this_week": services_this_week,
            "paginator_featured": paginator_featured,
            "is_paginated_featured": paginator_featured.num_pages > 1,
            "paginator_upcoming": paginator_upcoming,
            "is_paginated_upcoming": paginator_upcoming.num_pages > 1,
            "pagination_querystring": _pagination_querystring(request),
        },
    )


@login_required
def service_list(request):
    services = Service.objects.filter(is_published=True).select_related("created_by")
    search = request.GET.get("search", "").strip()
    duration = request.GET.get("duration", "").strip()
    appointment_type = request.GET.get("type", "").strip()

    if search:
        services = services.filter(Q(name__icontains=search) | Q(description__icontains=search))
    if duration:
        services = services.filter(duration_minutes=duration)
    if appointment_type:
        services = services.filter(appointment_type=appointment_type)

    paginator = Paginator(services, ITEMS_PER_PAGE)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "customer/service_list.html",
        {
            "services": page_obj,
            "paginator": paginator,
            "is_paginated": paginator.num_pages > 1,
            "pagination_querystring": _pagination_querystring(request),
            "search": search,
            "duration": duration,
            "type": appointment_type,
        },
    )


@login_required
def service_detail(request, service_id):
    service = get_object_or_404(Service, id=service_id, is_published=True)
    selected_date = _parse_date(request.GET.get("date"))
    working_hours = WorkingHours.objects.filter(service=service)
    questions = BookingQuestion.objects.filter(service=service)
    booking_rule = BookingRule.objects.filter(service=service).first()
    resources = Resource.objects.filter(service=service)
    available_slot_rows = _available_slot_rows(service, selected_date)

    return render(
        request,
        "customer/service_detail.html",
        {
            "service": service,
            "working_hours": working_hours,
            "slots": available_slot_rows,
            "available_slot_rows": available_slot_rows,
            "questions": questions,
            "booking_rule": booking_rule,
            "resources": resources,
            "selected_date": selected_date,
        },
    )


@login_required
def book_service(request, service_id):
    service = get_object_or_404(Service, id=service_id, is_published=True)
    questions = list(BookingQuestion.objects.filter(service=service))
    booking_rule = BookingRule.objects.filter(service=service).first()
    if request.method == "POST":
        raw_ad = (request.POST.get("appointment_date") or "").strip()
        selected_date = _parse_date(raw_ad or request.GET.get("date"))
    else:
        selected_date = _parse_date(request.GET.get("date"))
    slot_rows = _available_slot_rows(service, selected_date)
    available_slots = [row["slot"] for row in slot_rows]
    resources = Resource.objects.filter(service=service)

    slot_form = SlotSelectionForm(initial={"slot": request.POST.get("slot")})
    slot_form.fields["slot"].queryset = AppointmentSlot.objects.filter(
        id__in=[slot.id for slot in available_slots]
    )

    answers_payload = {}
    if request.method == "POST":
        slot_id = request.POST.get("slot")
        notes = request.POST.get("notes", "").strip()
        party_size = 1
        if booking_rule and booking_rule.manage_capacity:
            try:
                party_size = max(1, int(request.POST.get("party_size", "1")))
            except ValueError:
                party_size = 1
        if not slot_id:
            messages.error(request, "Please select a slot.")
            return redirect(f"{request.path}?date={selected_date:%Y-%m-%d}")
        status = "pending"
        if not (booking_rule and booking_rule.requires_manual_confirmation):
            status = "confirmed"

        missing_required = []
        for question in questions:
            answer_text = request.POST.get(f"question_{question.id}", "").strip()
            answers_payload[str(question.id)] = answer_text
            if question.is_required and not answer_text:
                missing_required.append(question.question_text)

        if missing_required:
            messages.error(request, "Please fill all required questions.")
            return render(
                request,
                "customer/book_service.html",
                {
                    "service": service,
                    "slot_form": slot_form,
                    "available_slots": available_slots,
                    "slot_rows": slot_rows,
                    "questions": questions,
                    "booking_rule": booking_rule,
                    "resources": resources,
                    "selected_date": selected_date,
                    "selected_slot_id": int(slot_id),
                    "answers_payload": answers_payload,
                    "notes_payload": notes,
                    "party_size": party_size,
                },
            )

        with transaction.atomic():
            slot = get_object_or_404(
                AppointmentSlot.objects.select_for_update(),
                id=slot_id,
                service=service,
            )
            spots_left = _spots_left(slot, selected_date)
            if party_size > spots_left:
                messages.error(
                    request,
                    f"This slot only has {spots_left} spot(s) left. Please adjust capacity.",
                )
                return redirect(f"{request.path}?date={selected_date:%Y-%m-%d}")

            selected_resource = None
            resource_id = request.POST.get("resource")
            if resource_id:
                selected_resource = Resource.objects.filter(id=resource_id, service=service).first()
            elif slot.resource_id:
                selected_resource = slot.resource

            booking = Booking.objects.create(
                customer=request.user,
                service=service,
                slot=slot,
                appointment_date=selected_date,
                party_size=party_size,
                assigned_resource=selected_resource,
                status=status,
                notes=notes,
            )

            for question in questions:
                answer_text = answers_payload.get(str(question.id), "").strip()
                if answer_text:
                    BookingAnswer.objects.create(
                        booking=booking, question=question, answer_text=answer_text
                    )

            if booking_rule and booking_rule.resource_assignment == "auto":
                resource = selected_resource or Resource.objects.filter(service=service).first()
                if resource:
                    booking.assigned_resource = resource
                    booking.save(update_fields=["assigned_resource"])

        return redirect("booking_confirmation", booking_id=booking.id)

    return render(
        request,
        "customer/book_service.html",
        {
            "service": service,
            "slot_form": slot_form,
            "available_slots": available_slots,
            "slot_rows": slot_rows,
            "questions": questions,
            "booking_rule": booking_rule,
            "resources": resources,
            "selected_date": selected_date,
            "selected_slot_id": None,
            "answers_payload": {},
            "notes_payload": "",
            "party_size": 1,
        },
    )


@login_required
def booking_confirmation(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related("service", "slot", "service__created_by"),
        id=booking_id,
        customer=request.user,
    )
    answers = BookingAnswer.objects.filter(booking=booking).select_related("question")
    return render(
        request, "customer/booking_confirmation.html", {"booking": booking, "answers": answers}
    )


@login_required
def my_bookings(request):
    all_bookings = (
        Booking.objects.filter(customer=request.user)
        .select_related("service", "slot", "service__created_by")
        .order_by("-booked_at")
    )
    status_filter = request.GET.get("status", "").strip()
    if status_filter:
        all_bookings = all_bookings.filter(status=status_filter)

    today = timezone.now().date()
    upcoming_list = all_bookings.filter(status__in=["pending", "confirmed"]).filter(
        Q(slot__date__gte=today) | Q(slot__date__isnull=True)
    )
    past_list = all_bookings.exclude(id__in=upcoming_list.values_list("id", flat=True))

    page_number = request.GET.get("page", 1)
    paginator_upcoming = Paginator(upcoming_list, ITEMS_PER_PAGE)
    paginator_past = Paginator(past_list, ITEMS_PER_PAGE)
    upcoming = paginator_upcoming.get_page(page_number)
    past = paginator_past.get_page(page_number)

    return render(
        request,
        "customer/my_bookings.html",
        {
            "upcoming": upcoming,
            "past": past,
            "status": status_filter,
            "paginator_upcoming": paginator_upcoming,
            "is_paginated_upcoming": paginator_upcoming.num_pages > 1,
            "paginator_past": paginator_past,
            "is_paginated_past": paginator_past.num_pages > 1,
            "pagination_querystring": _pagination_querystring(request),
        },
    )


@login_required
def booking_detail(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related("service", "slot", "service__created_by", "rescheduled_slot"),
        id=booking_id,
        customer=request.user,
    )
    answers = BookingAnswer.objects.filter(booking=booking).select_related("question")
    return render(
        request, "customer/booking_detail.html", {"booking": booking, "answers": answers}
    )


@login_required
@require_POST
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, customer=request.user)
    if booking.status in ["pending", "confirmed"]:
        booking.status = "cancelled"
        booking.save(update_fields=["status"])
        messages.success(request, "Your booking has been cancelled.")
    return redirect("my_bookings")


@login_required
def reschedule_booking(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related("service", "slot"),
        id=booking_id,
        customer=request.user,
    )
    if booking.status not in ["pending", "confirmed"]:
        messages.error(request, "This booking cannot be rescheduled.")
        return redirect("booking_detail", booking_id=booking.id)

    selected_date = _parse_date(request.POST.get("appointment_date") or request.GET.get("date"))
    slot_rows = [
        row
        for row in _available_slot_rows(booking.service, selected_date)
        if row["slot"].id != booking.slot_id
    ]
    available_slots = [row["slot"] for row in slot_rows]

    form = RescheduleForm(request.POST or None)
    form.fields["new_slot"].queryset = AppointmentSlot.objects.filter(
        id__in=[slot.id for slot in available_slots]
    )

    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            new_slot = get_object_or_404(
                AppointmentSlot.objects.select_for_update(),
                id=form.cleaned_data["new_slot"].id,
                service=booking.service,
            )
            if booking.party_size > _spots_left(new_slot, selected_date):
                messages.error(request, "That slot no longer has enough capacity.")
                return redirect(f"{request.path}?date={selected_date:%Y-%m-%d}")
            booking_rule = BookingRule.objects.filter(service=booking.service).first()
            booking.rescheduled_slot = booking.slot
            booking.slot = new_slot
            booking.appointment_date = selected_date
            booking.status = (
                "pending" if booking_rule and booking_rule.requires_manual_confirmation else "confirmed"
            )
            booking.save(update_fields=["rescheduled_slot", "slot", "appointment_date", "status"])
        messages.success(request, "Booking rescheduled successfully.")
        return redirect("booking_detail", booking_id=booking.id)

    return render(
        request,
        "customer/reschedule_booking.html",
        {
            "booking": booking,
            "form": form,
            "available_slots": available_slots,
            "slot_rows": slot_rows,
            "selected_date": selected_date,
        },
    )


@login_required
def profile(request):
    profile_obj, _ = CustomerProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = CustomerProfileForm(
            request.POST, request.FILES, instance=profile_obj
        )
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("customer_profile")
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = CustomerProfileForm(instance=profile_obj)

    upcoming_bookings_list = Booking.objects.filter(
        customer=request.user, status__in=["pending", "confirmed"]
    ).select_related("service", "slot").order_by("booked_at")
    past_bookings_list = Booking.objects.filter(
        customer=request.user, status__in=["cancelled", "rescheduled"]
    ).select_related("service", "slot").order_by("-booked_at")

    page_number = request.GET.get("page", 1)
    paginator_upcoming = Paginator(upcoming_bookings_list, ITEMS_PER_PAGE)
    paginator_past = Paginator(past_bookings_list, ITEMS_PER_PAGE)
    upcoming_bookings = paginator_upcoming.get_page(page_number)
    past_bookings = paginator_past.get_page(page_number)

    return render(
        request,
        "customer/profile.html",
        {
            "user_form": user_form,
            "profile_form": profile_form,
            "upcoming_bookings": upcoming_bookings,
            "past_bookings": past_bookings,
            "paginator_upcoming": paginator_upcoming,
            "is_paginated_upcoming": paginator_upcoming.num_pages > 1,
            "paginator_past": paginator_past,
            "is_paginated_past": paginator_past.num_pages > 1,
            "pagination_querystring": _pagination_querystring(request),
        },
    )
