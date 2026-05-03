from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Sum
from django.shortcuts import render

from booking.models import Appointment as CatalogAppointment
from customer.models import Booking
from organizer.models import Resource, Service

ITEMS_PER_PAGE = 10


def _pagination_querystring(request):
    q = request.GET.copy()
    q.pop("page", None)
    return q.urlencode()


def _is_admin(user):
    return user.is_authenticated and (
        user.is_superuser
        or getattr(getattr(user, "role_profile", None), "role", None) == "admin"
    )


def _account_role(user):
    p = getattr(user, "role_profile", None)
    return getattr(p, "role", "—") if p else "—"


def _combined_booking_rows():
    """
    Merges organizer-portal rows (customer.Booking) and catalog /book/ rows
    (booking.Appointment) so the admin dashboard reflects all live DB bookings.
    """
    rows = []
    for b in Booking.objects.select_related("customer", "service", "slot", "service__created_by").order_by(
        "-booked_at"
    ):
        u = b.customer
        rows.append(
            {
                "kind": "portal",
                "booked_at": b.booked_at,
                "reference_code": b.reference_code or "—",
                "ref_hint": f"{u.username} · {_account_role(u)}",
                "user_display": u.get_full_name() or u.username,
                "username": u.username,
                "role": _account_role(u),
                "provider": b.service.created_by.get_full_name()
                or b.service.created_by.email
                or b.service.created_by.username,
                "service_name": b.service.name,
                "display_date": b.display_date,
                "status": b.get_status_display(),
            }
        )

    for a in CatalogAppointment.objects.select_related(
        "user", "service", "timeslot", "service__category"
    ).order_by("-booked_at"):
        u = a.user
        rows.append(
            {
                "kind": "catalog",
                "booked_at": a.booked_at,
                "reference_code": a.reference_code or "—",
                "ref_hint": f"{u.username} · {_account_role(u)}",
                "user_display": u.get_full_name() or u.username,
                "username": u.username,
                "role": _account_role(u),
                "provider": "—",
                "service_name": a.service.name,
                "display_date": a.timeslot.date,
                "status": a.get_status_display(),
            }
        )

    rows.sort(key=lambda r: r["booked_at"], reverse=True)
    return rows


def _stats_and_booking_capacity():
    bookings_list = Booking.objects.select_related("customer", "service", "slot").order_by(
        "-booked_at"
    )
    portal_count = Booking.objects.count()
    catalog_count = CatalogAppointment.objects.count()
    stats = {
        "total_users": User.objects.count(),
        "organizers": User.objects.filter(role_profile__role="organizer").count(),
        "customers": User.objects.filter(role_profile__role="customer").count(),
        "total_services": Service.objects.count(),
        "published_services": Service.objects.filter(is_published=True).count(),
        "total_resources": Resource.objects.count(),
        "total_bookings": portal_count + catalog_count,
        "portal_bookings": portal_count,
        "catalog_appointments": catalog_count,
        "confirmed_bookings": Booking.objects.filter(status="confirmed").count()
        + CatalogAppointment.objects.filter(status=CatalogAppointment.STATUS_CONFIRMED).count(),
    }
    booking_capacity = bookings_list.aggregate(total=Sum("party_size"))["total"] or 0
    return stats, booking_capacity


@login_required
@user_passes_test(_is_admin, login_url="/accounts/login/")
def dashboard(request):
    stats, booking_capacity = _stats_and_booking_capacity()
    return render(
        request,
        "admin_dashboard/dashboard.html",
        {
            "stats": stats,
            "booking_capacity": booking_capacity,
            "active_page": "dashboard",
        },
    )


@login_required
@user_passes_test(_is_admin, login_url="/accounts/login/")
def user_management(request):
    users_list = User.objects.select_related("role_profile").order_by("-date_joined")
    role_filter = request.GET.get("role", "").strip()
    if role_filter:
        users_list = users_list.filter(role_profile__role=role_filter)

    page_number = request.GET.get("page", 1)
    paginator_users = Paginator(users_list, ITEMS_PER_PAGE)
    users_page = paginator_users.get_page(page_number)

    return render(
        request,
        "admin_dashboard/user_management.html",
        {
            "users": users_page,
            "paginator_users": paginator_users,
            "is_paginated_users": paginator_users.num_pages > 1,
            "selected_role": role_filter,
            "pagination_querystring": _pagination_querystring(request),
            "active_page": "users",
        },
    )


@login_required
@user_passes_test(_is_admin, login_url="/accounts/login/")
def services(request):
    services_list = Service.objects.select_related("created_by").order_by("-created_at")
    paginator = Paginator(services_list, ITEMS_PER_PAGE)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "admin_dashboard/services.html",
        {
            "services": page_obj,
            "paginator": paginator,
            "is_paginated": paginator.num_pages > 1,
            "pagination_querystring": _pagination_querystring(request),
            "active_page": "services",
        },
    )


@login_required
@user_passes_test(_is_admin, login_url="/accounts/login/")
def bookings(request):
    combined = _combined_booking_rows()
    paginator = Paginator(combined, ITEMS_PER_PAGE)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "admin_dashboard/bookings.html",
        {
            "bookings": page_obj,
            "paginator": paginator,
            "is_paginated": paginator.num_pages > 1,
            "pagination_querystring": _pagination_querystring(request),
            "active_page": "bookings",
        },
    )
