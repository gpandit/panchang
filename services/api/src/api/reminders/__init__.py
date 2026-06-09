"""Reminders & Scheduling module — Step 2.5.

Resolves Gregorian, Tithi, Nakshatra, and weekday recurrences into concrete
fire-times per user location, then fans out to APNs / FCM / email via a
queue-driven delivery service.

Architecture north-star §3 (component 04): recurrence resolution reads the
cached Panchang; delivery never blocks interactive requests.
"""
