
"""
booking_rules.py — business rules for the Richfield Booking System.

Responsibilities:
- Validate booking dates, times and durations.
- Enforce campus booking policies.
- Detect overlapping bookings.
- Create and cancel bookings.
"""

from datetime import date, datetime, timedelta


TIME_FORMAT = "%H:%M"
DATE_FORMAT = "%Y-%m-%d"


class BookingError(Exception):
    """Raised when a booking violates a business rule."""


def parse_date(booking_date):
    """Validate and convert a date in YYYY-MM-DD format."""
    try:
        parsed = datetime.strptime(booking_date, DATE_FORMAT).date()
    except (ValueError, TypeError):
        raise BookingError("Date must use YYYY-MM-DD format.")

    if parsed < date.today():
        raise BookingError("You cannot book a resource in the past.")

    return parsed


def parse_time(start_time):
    """Validate and convert a time in HH:MM format."""
    try:
        return datetime.strptime(start_time, TIME_FORMAT).time()
    except (ValueError, TypeError):
        raise BookingError("Time must use HH:MM format, for example 09:30.")


def validate_booking(conn, user_id, resource_id, booking_date,
                     start_time, duration_minutes):
    """
    Validate a proposed booking.

    Returns True if valid.
    Raises BookingError if any rule is violated.
    """

    # Validate date and time formats.
    parsed_date = parse_date(booking_date)
    parsed_time = parse_time(start_time)

    # Validate duration.
    if isinstance(duration_minutes, bool) or not isinstance(
        duration_minutes, int
    ):
        raise BookingError("Duration must be a whole number of minutes.")

    if duration_minutes <= 0:
        raise BookingError("Duration must be greater than zero.")

    # Verify that the user exists.
    user = conn.execute(
        "SELECT user_id FROM users WHERE user_id = ?",
        (user_id,)
    ).fetchone()

    if user is None:
        raise BookingError("The selected user does not exist.")

    # Find the selected resource and its campus policy.
    resource = conn.execute(
        """
        SELECT r.resource_id, r.campus_id, r.name,
               c.max_duration_minutes, c.closing_time
        FROM resources AS r
        JOIN campuses AS c ON c.campus_id = r.campus_id
        WHERE r.resource_id = ?
        """,
        (resource_id,)
    ).fetchone()

    if resource is None:
        raise BookingError("The selected resource does not exist.")

    # Enforce the campus duration limit.
    if duration_minutes > resource["max_duration_minutes"]:
        raise BookingError(
            f"This campus allows bookings up to "
            f"{resource['max_duration_minutes']} minutes."
        )

    # Calculate the booking's finish time.
    start_minutes = parsed_time.hour * 60 + parsed_time.minute
    end_minutes = start_minutes + duration_minutes

    if end_minutes > 24 * 60:
        raise BookingError("A booking cannot continue into the next day.")

    # Enforce an optional campus closing time.
    closing_time = resource["closing_time"]

    if closing_time:
        closing = parse_time(closing_time)
        closing_minutes = closing.hour * 60 + closing.minute

        if end_minutes > closing_minutes:
            raise BookingError(
                f"The booking must finish by {closing_time}."
            )

    # Reject bookings that have already ended today.
    if parsed_date == date.today():
        now = datetime.now()
        if end_minutes <= now.hour * 60 + now.minute:
            raise BookingError("This booking would already have ended.")

    # Check overlapping active bookings for the same resource.
    existing = conn.execute(
        """
        SELECT start_time, duration_minutes
        FROM bookings
        WHERE resource_id = ?
          AND booking_date = ?
          AND status = 'active'
        """,
        (resource_id, booking_date)
    ).fetchall()

    for booking in existing:
        old_start = parse_time(booking["start_time"])
        old_start_minutes = old_start.hour * 60 + old_start.minute
        old_end_minutes = (
            old_start_minutes + booking["duration_minutes"]
        )

        # Intervals overlap if each starts before the other finishes.
        if (
            start_minutes < old_end_minutes
            and old_start_minutes < end_minutes
        ):
            raise BookingError(
                "This resource is already booked during that time."
            )

    return True


def create_booking(conn, user_id, resource_id, booking_date,
                   start_time, duration_minutes):
    """Validate and save a booking."""

    validate_booking(
        conn,
        user_id,
        resource_id,
        booking_date,
        start_time,
        duration_minutes
    )

    try:
        cursor = conn.execute(
            """
            INSERT INTO bookings
                (user_id, resource_id, booking_date,
                 start_time, duration_minutes, status)
            VALUES (?, ?, ?, ?, ?, 'active')
            """,
            (
                user_id,
                resource_id,
                booking_date,
                start_time,
                duration_minutes
            )
        )
        conn.commit()
        return cursor.lastrowid

    except Exception:
        conn.rollback()
        raise


def cancel_booking(conn, booking_id, user_id=None):
    """
    Cancel an active booking.

    If user_id is supplied, only that user's booking can be cancelled
    through this function. Administrative authorisation must be checked
    by the calling layer.
    """

    query = """
        UPDATE bookings
        SET status = 'cancelled'
        WHERE booking_id = ?
          AND status = 'active'
    """
    params = [booking_id]

    if user_id is not None:
        query += " AND user_id = ?"
        params.append(user_id)

    cursor = conn.execute(query, params)

    if cursor.rowcount == 0:
        conn.rollback()
        raise BookingError(
            "No matching active booking was found, or you cannot cancel it."
        )

    conn.commit()
    return True


def get_user_bookings(conn, user_id):
    """Return a user's bookings, including cancelled booking history."""
    return conn.execute(
        """
        SELECT b.booking_id, b.resource_id, r.name AS resource_name,
               c.name AS campus_name, b.booking_date, b.start_time,
               b.duration_minutes, b.status, b.created_at
        FROM bookings AS b
        JOIN resources AS r ON r.resource_id = b.resource_id
        JOIN campuses AS c ON c.campus_id = r.campus_id
        WHERE b.user_id = ?
        ORDER BY b.booking_date DESC, b.start_time DESC
        """,
        (user_id,)
    ).fetchall()


def get_available_resources(conn, booking_date, start_time,
                            duration_minutes, campus_id=None):
    """
    Return resources with no active booking overlapping the requested time.

    This function checks resource availability. It does not replace
    validate_booking() when a booking is created.
    """

    parsed_date = parse_date(booking_date)
    parsed_time = parse_time(start_time)

    if isinstance(duration_minutes, bool) or not isinstance(
        duration_minutes, int
    ) or duration_minutes <= 0:
        raise BookingError("Duration must be a positive whole number.")

    start_minutes = parsed_time.hour * 60 + parsed_time.minute
    end_minutes = start_minutes + duration_minutes

    if end_minutes > 24 * 60:
        raise BookingError("A booking cannot continue into the next day.")

    if parsed_date == date.today():
        now = datetime.now()
        if end_minutes <= now.hour * 60 + now.minute:
            raise BookingError("This booking would already have ended.")

    sql = """
        SELECT r.resource_id, r.name, r.resource_type, r.capacity,
               c.campus_id, c.name AS campus_name,
               c.max_duration_minutes, c.closing_time
        FROM resources AS r
        JOIN campuses AS c ON c.campus_id = r.campus_id
        WHERE 1 = 1
    """
    params = []

    if campus_id is not None:
        sql += " AND c.campus_id = ?"
        params.append(campus_id)

    resources = conn.execute(sql, params).fetchall()
    available = []

    for resource in resources:
        if duration_minutes > resource["max_duration_minutes"]:
            continue

        closing_time = resource["closing_time"]

        if closing_time:
            closing = parse_time(closing_time)
            closing_minutes = closing.hour * 60 + closing.minute
            if end_minutes > closing_minutes:
                continue

        existing = conn.execute(
            """
            SELECT start_time, duration_minutes
            FROM bookings
            WHERE resource_id = ?
              AND booking_date = ?
              AND status = 'active'
            """,
            (resource["resource_id"], booking_date)
        ).fetchall()

        conflict = False

        for booking in existing:
            old_start = parse_time(booking["start_time"])
            old_start_minutes = old_start.hour * 60 + old_start.minute
            old_end_minutes = (
                old_start_minutes + booking["duration_minutes"]
            )

            if (
                start_minutes < old_end_minutes
                and old_start_minutes < end_minutes
            ):
                conflict = True
                break

        if not conflict:
            available.append(resource)

    return available
