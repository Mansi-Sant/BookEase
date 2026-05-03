-- =============================================================================
-- BookEase / appointment_system — seed data (PostgreSQL)
-- =============================================================================
--
-- RECOMMENDED (keeps reference_code, slots, and FKs consistent):
--   python manage.py seed_data
--
-- This file documents the same data model and provides:
--   * A known password hash for "Test@1234" (Django pbkdf2)
--   * Optional bulk SQL patterns (auth + role profiles) via generate_series
--   * Verification queries for all application tables
--
-- If you only need extra auth rows in SQL, use SECTION A below, then run
--   python manage.py seed_data
-- to fill organizer / booking / customer tables (50+ rows each).
--
-- Default database (from settings): name=appointment_db, user=postgres, port=5432
--   psql -U postgres -d appointment_db -f seed_data.sql
-- =============================================================================

-- Hash for password: Test@1234  (regenerate: python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','appointment_system.settings'); import django; django.setup(); from django.contrib.auth.hashers import make_password; print(make_password('Test@1234'))")
-- v2026-05-03
\set pwdhash 'pbkdf2_sha256$600000$j0JZlwKI79ToINb7JYXlE3$6E/JyrzyvdrEZVDGlz/kFymqXXQt38Wc50U8sEGrVX0='

-- =============================================================================
-- SECTION A (optional) — bulk users 1..50 + accounts_userprofile (SQL-only)
-- =============================================================================
-- Uncomment to insert customers when usernames do not already exist.
-- Safe re-run: NOT if user names conflict — prefer TRUNCATE (destructive) or skip.

/*
SET session_replication_role = replica;

INSERT INTO auth_user (password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined)
SELECT
  :'pwdhash',
  NULL, false,
  'sql_customer_' || lpad(i::text, 2, '0'),
  'SQL', 'Customer' || i,
  'sqlcustomer' || lpad(i::text, 2, '0') || '@bookease.com',
  false, true, NOW()
FROM generate_series(1, 50) AS s(i)
ON CONFLICT DO NOTHING;

INSERT INTO accounts_userprofile (role, user_id, phone_number)
SELECT 'customer', u.id, '+1788' || lpad(gs.i::text, 7, '0')
FROM generate_series(1, 50) AS gs(i)
JOIN auth_user u ON u.username = 'sql_customer_' || lpad(gs.i::text, 2, '0')
ON CONFLICT DO NOTHING;

SET session_replication_role = DEFAULT;
*/

-- =============================================================================
-- SECTION B — verification (run after python manage.py seed_data)
-- =============================================================================
-- Expect ≥ 50 rows each where noted.

SELECT 'auth_user total' AS metric, COUNT(*)::text AS value FROM auth_user;
SELECT 'accounts_userprofile' AS metric, COUNT(*)::text FROM accounts_userprofile;
SELECT 'accounts_otprecord' AS metric, COUNT(*)::text FROM accounts_otprecord;

SELECT 'booking_servicecategory' AS metric, COUNT(*)::text FROM booking_servicecategory;
SELECT 'booking_service' AS metric, COUNT(*)::text FROM booking_service;
SELECT 'booking_timeslot' AS metric, COUNT(*)::text FROM booking_timeslot;
SELECT 'booking_appointment' AS metric, COUNT(*)::text FROM booking_appointment;
SELECT 'booking_appointment with reference_code' AS metric, COUNT(*)::text
  FROM booking_appointment WHERE reference_code IS NOT NULL AND reference_code <> '';
SELECT 'booking_userprofile' AS metric, COUNT(*)::text FROM booking_userprofile;

SELECT 'organizer_service' AS metric, COUNT(*)::text FROM organizer_service;
SELECT 'organizer_resource' AS metric, COUNT(*)::text FROM organizer_resource;
SELECT 'organizer_workinghours' AS metric, COUNT(*)::text FROM organizer_workinghours;
SELECT 'organizer_appointmentslot' AS metric, COUNT(*)::text FROM organizer_appointmentslot;
SELECT 'organizer_bookingquestion' AS metric, COUNT(*)::text FROM organizer_bookingquestion;
SELECT 'organizer_bookingrule' AS metric, COUNT(*)::text FROM organizer_bookingrule;

SELECT 'customer_customerprofile' AS metric, COUNT(*)::text FROM customer_customerprofile;
SELECT 'customer_booking' AS metric, COUNT(*)::text FROM customer_booking;
SELECT 'customer_bookinganswer' AS metric, COUNT(*)::text FROM customer_bookinganswer;

-- Sample reference codes (booking.Appointment)
SELECT reference_code, status, booked_at
FROM booking_appointment
ORDER BY id
LIMIT 10;
