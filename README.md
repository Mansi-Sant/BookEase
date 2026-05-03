# BookEase — Appointment Booking System

Odoo-inspired appointment portal for the Django × PostgreSQL hackathon stack. All catalog, slots, and appointments are loaded from **PostgreSQL** via the Django ORM (no hardcoded lists in views).

## Folder structure

```
appointment_system/
├── appointment_system/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── booking/
│   ├── migrations/
│   ├── templates/
│   │   └── booking/
│   │       ├── base.html
│   │       ├── home.html
│   │       ├── login.html
│   │       ├── signup.html
│   │       ├── dashboard.html
│   │       ├── services.html
│   │       ├── book_appointment.html
│   │       ├── my_appointments.html
│   │       └── confirmation.html
│   ├── static/
│   │   └── booking/
│   │       ├── css/
│   │       │   └── style.css
│   │       └── js/
│   │           └── main.js
│   ├── management/
│   │   └── commands/
│   │       └── seed_data.py
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── forms.py
│   └── utils.py
├── manage.py
├── requirements.txt
├── seed_sample.sql          # optional illustrative SQL
├── .gitignore
└── README.md
```

## Requirements

- Python 3.10+
- PostgreSQL 14+ (or compatible)

## Environment variables

Create a `.env` file in the project root (see `.gitignore`; never commit secrets):

| Variable       | Description           | Example        |
|----------------|-----------------------|----------------|
| `SECRET_KEY`   | Django secret         | long random string |
| `DEBUG`        | Debug flag            | `True` / `False` |
| `ALLOWED_HOSTS`| Comma-separated hosts | `localhost,127.0.0.1` |
| `DB_NAME`      | Database name         | `appointment_db` |
| `DB_USER`      | DB user               | `postgres` |
| `DB_PASSWORD`  | DB password           | your password |
| `DB_HOST`      | DB host               | `localhost` |
| `DB_PORT`      | DB port               | `5432` |

## Current simplified scope

This build follows the problem statement without OTP/payment complexity:

- Email and password signup/login for customers and organizers.
- Admin control panel at `/control-panel/` for totals, users, providers, roles, and account activation.
- Organizer service setup with appointment type, resources, working hours, weekly/flexible slots, custom booking questions, capacity rules, manual confirmation, publish/unpublish, booking list, and basic reports.
- Customer discovery, date-based slot selection, resource preference, capacity/party size, booking questions, confirmation, cancel, reschedule, and profile history.
- Capacity is checked again inside a database transaction before booking/rescheduling to reduce double-booking risk.

## Setup

```bash
python -m venv venv
# Windows: venv\Scripts\activate
# Unix:    source venv/bin/activate

pip install -r requirements.txt

# Create database appointment_db in PostgreSQL, then:
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_data
python manage.py runserver
```

Open http://127.0.0.1:8000/

Use `/accounts/signup/` for customer/organizer accounts. Use `/control-panel/` with a Django superuser for the admin dashboard.

## Seed data

- **Idempotent (recommended):** `python manage.py seed_data` — 3 categories, 10 services, and 210 time slots (7 days × 10 services × 3 starts per day) in the rolling week window.
- **Sample SQL:** see `seed_sample.sql` for a minimal illustrative `INSERT` pattern (management command is safer for FKs and `end_time`).

## Screenshots

_Add screenshots of Home, Services, Book flow, Dashboard, and Confirmation for your hackathon submission._

## Design notes

- **UI:** Vanilla HTML/CSS/JS, Inter font, Odoo teal `#00A09D` and purple `#875A7B`.
- **Booking:** Service pick triggers a Django `POST` (`select_slots`) to refresh slots; confirm step uses client-side validation plus `Appointment` `clean()` and `unique_together` on `(user, timeslot)`.
- **Pinned deps:** see `requirements.txt` (Django 4.2.13, psycopg2-binary 2.9.9, etc.).

## License

Demo / educational use for hackathon judging.
