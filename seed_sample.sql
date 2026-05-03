-- Sample PostgreSQL seed for BookEase (illustrative).
-- Recommended for demos:  python manage.py migrate  &&  python manage.py seed_data
-- Table names assume default Django app label `booking` and no custom db_table.

-- 3 categories
INSERT INTO booking_servicecategory (name, icon_emoji, description) VALUES
  ('Healthcare', '🏥', 'Medical and wellness consultations.'),
  ('Fitness', '🏋️', 'Training and movement sessions.'),
  ('Beauty', '💇', 'Salon and spa-style services.');

-- Example: one service per category (add more with further INSERTs using category_id from above)
INSERT INTO booking_service (category_id, name, description, duration_minutes, price, is_active)
SELECT id, 'Dental checkup', 'Routine exam and cleaning.', 30, 85.00, true
FROM booking_servicecategory WHERE name = 'Healthcare' LIMIT 1;

INSERT INTO booking_service (category_id, name, description, duration_minutes, price, is_active)
SELECT id, 'Personal training', '1:1 strength and conditioning.', 60, 75.00, true
FROM booking_servicecategory WHERE name = 'Fitness' LIMIT 1;

INSERT INTO booking_service (category_id, name, description, duration_minutes, price, is_active)
SELECT id, 'Haircut & style', 'Cut and finish.', 30, 45.00, true
FROM booking_servicecategory WHERE name = 'Beauty' LIMIT 1;

-- Example time slots: next 7 days at 09:00 UTC date — adjust dates as needed
INSERT INTO booking_timeslot (service_id, date, start_time, end_time, is_available, max_capacity)
SELECT s.id, CURRENT_DATE + d.day, '09:00'::time, '09:30'::time, true, 1
FROM booking_service s
CROSS JOIN generate_series(0, 6) AS d(day)
WHERE s.name = 'Dental checkup'
LIMIT 7;
