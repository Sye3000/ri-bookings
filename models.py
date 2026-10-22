
"""models.py — user models for the Richfield Booking System."""


class User:
    """Base class containing shared user information."""

    def __init__(self, user_id, username, full_name, role, campus_id=None):
        self.user_id = user_id
        self.username = username
        self.full_name = full_name
        self.role = role
        self.campus_id = campus_id

    def get_details(self):
        """Return basic user information."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role,
            "campus_id": self.campus_id,
        }


class Lecturer(User):
    """A lecturer who can manage their own bookings."""

    def __init__(self, user_id, username, full_name):
        super().__init__(
            user_id, username, full_name, "lecturer"
        )


class CampusAdmin(User):
    """An administrator responsible for one campus."""

    def __init__(self, user_id, username, full_name, campus_id):
        super().__init__(
            user_id, username, full_name, "campus_admin", campus_id
        )


class SystemOperator(User):
    """An operator responsible for system-wide administration."""

    def __init__(self, user_id, username, full_name):
        super().__init__(
            user_id, username, full_name, "system_operator"
        )


def create_user_from_row(row):
    """Convert a database user row into the correct Python object."""
    role = row["role"]

    if role == "lecturer":
        return Lecturer(
            row["user_id"],
            row["username"],
            row["full_name"],
        )

    if role == "campus_admin":
        return CampusAdmin(
            row["user_id"],
            row["username"],
            row["full_name"],
            row["campus_id"],
        )

    if role == "system_operator":
        return SystemOperator(
            row["user_id"],
            row["username"],
            row["full_name"],
        )

    raise ValueError(f"Unsupported user role: {role}")
