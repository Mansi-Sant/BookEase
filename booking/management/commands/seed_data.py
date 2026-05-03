"""
Seed PostgreSQL with demo data via the Django ORM.

Creates at least 50 rows per app-owned table (where applicable):
  accounts: UserProfile roles, OTPRecord
  organizer: Service, Resource, WorkingHours, AppointmentSlot, BookingQuestion, BookingRule
  booking: ServiceCategory, Service, TimeSlot, Appointment (reference_code auto), UserProfile
  customer: CustomerProfile, Booking, BookingAnswer

Also ensures 50 customer + 50 organizer auth users (password: Test@1234).

Usage:
  python manage.py seed_data
  python manage.py seed_data --skip-booking-app   # only users + organizer + customer chain
"""

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone

from accounts.models import OTPRecord
from customer.models import Booking as CustomerBooking
from customer.models import BookingAnswer
from organizer.models import (
    AppointmentSlot,
    BookingQuestion,
    BookingRule,
    Resource,
    Service as OrganizerService,
    WorkingHours,
)

from booking.models import Appointment as BookingAppointment
from booking.models import Service as BookingCatalogService
from booking.models import ServiceCategory
from booking.models import TimeSlot

User = get_user_model()

SEED_COUNT = 50
DEFAULT_PASSWORD = "Test@1234"

ORG_APPOINTMENT_TYPES = ("one_to_one", "group", "resource")
BOOKING_STATUSES = (
    BookingAppointment.STATUS_CONFIRMED,
    BookingAppointment.STATUS_PENDING,
    BookingAppointment.STATUS_COMPLETED,
)
CUSTOMER_BOOKING_STATUSES = ("confirmed", "pending", "cancelled")


def _ensure_user(username, email, first_name, last_name, role):
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "is_staff": False,
            "is_superuser": False,
            "is_active": True,
        },
    )
    if not created:
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.is_staff = False
        user.is_superuser = False
        user.is_active = True
    user.set_password(DEFAULT_PASSWORD)
    user.save()

    profile = user.role_profile
    if profile.role != role:
        profile.role = role
        profile.save(update_fields=["role"])

    return user, created


def _seed_users(stdout):
    """50 customers + 50 organizers; stable usernames customer_01 .. customer_50."""
    added_c = added_o = 0
    for i in range(1, SEED_COUNT + 1):
        label = f"{i:02d}"
        _, c = _ensure_user(
            f"customer_{label}",
            f"customer{label}@bookease.com",
            "Demo",
            f"Customer{label}",
            "customer",
        )
        if c:
            added_c += 1
        _, c = _ensure_user(
            f"organizer_{label}",
            f"organizer{label}@bookease.com",
            "Demo",
            f"Organizer{label}",
            "organizer",
        )
        if c:
            added_o += 1

    for i in range(1, SEED_COUNT + 1):
        label = f"{i:02d}"
        u = User.objects.get(username=f"customer_{label}")
        p = u.role_profile
        phone = f"+1555{label}0001"
        if p.phone_number != phone:
            p.phone_number = phone
            p.save(update_fields=["phone_number"])

        uo = User.objects.get(username=f"organizer_{label}")
        po = uo.role_profile
        phone_o = f"+1666{label}0001"
        if po.phone_number != phone_o:
            po.phone_number = phone_o
            po.save(update_fields=["phone_number"])

    stdout.write(
        f"  Users: new customers={added_c}, new organizers={added_o} "
        f"(total customers with profile={User.objects.filter(role_profile__role='customer').count()})."
    )


def _seed_otp(stdout):
    created = 0
    for i in range(1, SEED_COUNT + 1):
        ident = f"otpseed{i:02d}@bookease.com"
        obj, was_created = OTPRecord.objects.get_or_create(
            identifier=ident,
            method="email",
            defaults={
                "otp_code": f"{(i * 7919) % 1000000:06d}",
                "role": "customer",
                "is_used": i % 4 == 0,
            },
        )
        if was_created:
            created += 1
    stdout.write(f"  OTPRecord: created {created}; total={OTPRecord.objects.count()}.")


def _seed_organizer_graph(stdout):
    """
    Per index i in 1..50: one organizer Service (by organizer_i), Resource, WorkingHours,
    BookingRule, BookingQuestion, AppointmentSlot (flexible date).
    """
    today = timezone.localdate()
    svc_created = res_created = wh_created = slot_created = q_created = br_created = 0

    org_slots = []
    org_questions = []

    for i in range(1, SEED_COUNT + 1):
        label = f"{i:02d}"
        owner = User.objects.get(username=f"organizer_{label}")
        duration = [30, 45, 60, 90, 120][(i - 1) % 5]
        appt_type = ORG_APPOINTMENT_TYPES[(i - 1) % len(ORG_APPOINTMENT_TYPES)]

        svc, s_created = OrganizerService.objects.get_or_create(
            name=f"Portal Offering {label}",
            created_by=owner,
            defaults={
                "description": (
                    f"Seeded organizer catalog item #{i}. Reference list price: "
                    f"₹{(500 + i * 17) % 10000}.00."
                ),
                "duration_minutes": duration,
                "appointment_type": appt_type,
                "venue": f"Venue hub {label}",
                "is_published": True,
            },
        )
        if s_created:
            svc_created += 1

        res, r_created = Resource.objects.get_or_create(
            service=svc,
            name=f"Staff / room {label}",
            defaults={"assigned_user": owner},
        )
        if r_created:
            res_created += 1

        dow = (i - 1) % 7
        wh, w_created = WorkingHours.objects.get_or_create(
            service=svc,
            day_of_week=dow,
            start_time=time(9, 0),
            end_time=time(17, 0),
        )
        if w_created:
            wh_created += 1

        _, br_new = BookingRule.objects.get_or_create(
            service=svc,
            defaults={
                "max_bookings_per_slot": 3 if appt_type == "group" else 1,
                "manage_capacity": True,
                "advance_payment_enabled": False,
                "requires_manual_confirmation": i % 10 == 0,
                "resource_assignment": BookingRule.ASSIGNMENT_AUTO,
            },
        )
        if br_new:
            br_created += 1

        q_text = f"Anything we should know for booking #{label}?"
        bq, q_new = BookingQuestion.objects.get_or_create(
            service=svc,
            question_text=q_text,
            defaults={"is_required": i % 2 == 0},
        )
        org_questions.append(bq)
        if q_new:
            q_created += 1

        slot_date = today + timedelta(days=i)
        start_t = time(10, 0)
        naive_end = datetime.combine(slot_date, start_t) + timedelta(minutes=duration)
        end_t = naive_end.time()

        slot, sl_created = AppointmentSlot.objects.get_or_create(
            service=svc,
            schedule_type=AppointmentSlot.SCHEDULE_FLEXIBLE,
            date=slot_date,
            start_time=start_t,
            defaults={
                "end_time": end_t,
                "max_bookings": 4 if appt_type == "group" else 2,
                "resource": res,
                "day_of_week": None,
            },
        )
        org_slots.append(slot)
        if sl_created:
            slot_created += 1

    stdout.write(
        "  Organizer: "
        f"services +{svc_created} / {OrganizerService.objects.count()}, "
        f"resources +{res_created}, working_hours +{wh_created}, "
        f"slots +{slot_created}, questions +{q_created}, rules +{br_created}."
    )
    return org_slots, org_questions


def _seed_booking_app(stdout):
    """booking app: categories, catalog services, timeslots, appointments with reference_code."""
    today = timezone.localdate()
    durations = [15, 30, 45, 60, 90]
    categories = []
    for i in range(1, SEED_COUNT + 1):
        label = f"{i:02d}"
        cat, _ = ServiceCategory.objects.get_or_create(
            name=f"Seed Category {label}",
            defaults={
                "icon_emoji": ["📅", "✂️", "💇", "🦷", "💼"][i % 5],
                "description": f"Demo navigation category #{i}",
            },
        )
        categories.append(cat)

    booking_services = []
    for i in range(1, SEED_COUNT + 1):
        label = f"{i:02d}"
        dur = durations[(i - 1) % len(durations)]
        bs, _ = BookingCatalogService.objects.get_or_create(
            name=f"Catalog Service {label}",
            category=categories[i - 1],
            defaults={
                "description": f"MVP catalog row #{i} for hackathon judges.",
                "duration_minutes": dur,
                "price": Decimal("49.99") + Decimal(i),
                "is_active": True,
            },
        )
        booking_services.append(bs)

    timeslots = []
    for i in range(1, SEED_COUNT + 1):
        bs = booking_services[i - 1]
        d = today + timedelta(days=SEED_COUNT + i)
        ts, _ = TimeSlot.objects.get_or_create(
            service=bs,
            date=d,
            start_time=time(11, 30),
            defaults={"is_available": True, "max_capacity": 1},
        )
        timeslots.append(ts)

    ap_new = 0
    for i in range(1, SEED_COUNT + 1):
        label = f"{i:02d}"
        cust = User.objects.get(username=f"customer_{label}")
        appt, created = BookingAppointment.objects.get_or_create(
            user=cust,
            timeslot=timeslots[i - 1],
            defaults={
                "service": booking_services[i - 1],
                "status": BOOKING_STATUSES[(i - 1) % len(BOOKING_STATUSES)],
                "notes": f"Seeded appointment #{i} (reference_code auto).",
            },
        )
        if created:
            ap_new += 1
            TimeSlot.objects.filter(pk=timeslots[i - 1].pk).update(is_available=False)

    stdout.write(
        f"  booking app: appointments +{ap_new} / {BookingAppointment.objects.count()} "
        f"(all carry reference_code)."
    )


def _seed_customer_rows(stdout, org_slots, org_questions):
    created_b = created_a = 0
    for i in range(1, SEED_COUNT + 1):
        label = f"{i:02d}"
        cust = User.objects.get(username=f"customer_{label}")
        booking, b_new = CustomerBooking.objects.get_or_create(
            customer=cust,
            slot=org_slots[i - 1],
            defaults={
                "service": org_slots[i - 1].service,
                "appointment_date": org_slots[i - 1].date,
                "party_size": 1 + (i % 3),
                "assigned_resource": org_slots[i - 1].resource,
                "status": CUSTOMER_BOOKING_STATUSES[(i - 1) % len(CUSTOMER_BOOKING_STATUSES)],
                "notes": f"Seeded portal booking #{i}",
            },
        )
        if b_new:
            created_b += 1

        _, an_new = BookingAnswer.objects.get_or_create(
            booking=booking,
            question=org_questions[i - 1],
            defaults={"answer_text": f"Sample answer for booking #{label}."},
        )
        if an_new:
            created_a += 1

    stdout.write(
        f"  customer: bookings +{created_b} this run; BookingAnswer +{created_a} "
        f"(total bookings {CustomerBooking.objects.count()}, "
        f"answers {BookingAnswer.objects.count()})."
    )


class Command(BaseCommand):
    help = (
        f"Load demo data: {SEED_COUNT} rows per table (users, organizer, booking app, "
        "customer). Password for seeded users: "
        + DEFAULT_PASSWORD
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-booking-app",
            action="store_true",
            help="Skip booking.Service / TimeSlot / Appointment (reference_code) seeding.",
        )

    def handle(self, *args, **options):
        skip_booking = options["skip_booking_app"]
        self.stdout.write(
            self.style.NOTICE(
                f"Seeding database engine={connection.vendor!r} alias={connection.alias!r}"
            )
        )

        with transaction.atomic():
            _seed_users(self.stdout)
            _seed_otp(self.stdout)
            org_slots, org_questions = _seed_organizer_graph(self.stdout)
            if not skip_booking:
                _seed_booking_app(self.stdout)
            _seed_customer_rows(self.stdout, org_slots, org_questions)

        ref_ok = BookingAppointment.objects.exclude(reference_code="").count()
        self.stdout.write(
            self.style.SUCCESS(
                "Done.\n"
                f"  booking.Appointment rows with reference_code set: {ref_ok} / "
                f"{BookingAppointment.objects.count()}.\n"
                "  Login sample: customer_01 / "
                + DEFAULT_PASSWORD
                + "  |  organizer_01 / "
                + DEFAULT_PASSWORD
            )
        )
