# Richfield Booking Management System

A desktop booking application built with **Python**, **Tkinter**, and
**SQLite**. It manages campus resources and bookings and applies rules
such as campus duration limits, closing times, and prevention of
overlapping active bookings.

## Features

### Lecturer

-   Sign in to the application.
-   View campus resources.
-   Check resource availability through the booking workflow.
-   Create bookings for available resources.
-   View personal booking history.
-   Cancel personal active bookings.

### Campus Administrator

-   View campus overview counts for resources, users, and bookings.
-   View resources belonging to their campus.
-   View and manage bookings for their campus.
-   Cancel active bookings for resources belonging to their campus.
-   View users assigned to their campus.

### System Operator

-   View system-wide counts for campuses, users, resources, and
    bookings.
-   View resources across all campuses.

### Booking rules

-   Validate booking dates, times, and duration.
-   Apply campus maximum-duration limits.
-   Enforce a campus closing time when configured.
-   Reject overnight bookings and bookings that have already ended.
-   Prevent overlapping active bookings for the same resource.
-   Make a time slot available again after a booking is cancelled.

## Technology

-   **Language:** Python 3
-   **GUI:** Tkinter and `ttk`
-   **Database:** SQLite
-   **External Python packages:** None required for the core application

## Project structure

``` text
booking-system/
├── main.py       # Application entry point
├── gui.py        # Login and role-specific graphical interfaces
├── database.py   # SQLite connection, schema, and seed data
├── models.py     # Data/model-related code
├── rules.py      # Booking validation and booking operations
├── stage1.py     # Booking-rule tests
└── richfield.db  # Local SQLite database, if included
```

Local backup files may also be present; they are not required to run the
application.

## Requirements

-   Python 3
-   Tkinter
-   A desktop environment that can display a graphical interface

SQLite is included with most standard Python installations.

### Install Tkinter on Linux Mint / Ubuntu

If Tkinter is missing, run:

``` bash
sudo apt update
sudo apt install python3-tk
```

## Run the application

Open a terminal in the project directory and run:

``` bash
python3 main.py
```

If the project is stored at `~/booking-system`, you can first run:

``` bash
cd ~/booking-system
```

## Run the tests

Run the following from the project directory:

``` bash
python3 stage1.py
```

The Stage 1 test suite checks: - Valid booking creation - Overlap
prevention - Campus duration limits - Closing-time policy - Releasing a
slot after cancellation - Rejection of invalid duration

Run the tests on your own copy to confirm the current state. You can
also check Python syntax with:

``` bash
python3 -m py_compile main.py gui.py database.py models.py rules.py stage1.py
```

## Database and demo accounts

The application uses a local SQLite database file named `richfield.db`.
If that file is included, it may contain development/demo data and
accounts.

Demo credentials used during development:

  Role                   Username       Password
  ---------------------- -------------- ----------------
  System Operator        `operator`     `Operator123`
  Campus Administrator   `admin_a`      `AdminA123`
  Campus Administrator   `admin_b`      `AdminB123`
  Campus Administrator   `admin_c`      `AdminC123`
  Lecturer               `lecturer_a`   `LecturerA123`

The lecturer account was added manually during development, so it may
not exist in a newly initialized database. Which accounts are available
depends on the database file and its initialization state.

**Security note:** These are development/demo credentials, not
production credentials. Change or remove them before deploying the
application or using it with real data.

## Current scope and limitations

This is a developing academic project. The features listed here reflect
the functionality implemented during development; verify the application
and tests before relying on it. Some management screens are view-only,
and the application is not yet a production-ready deployment.

## Sharing the project

Include the Python source files when sharing the project. If the
recipient needs the same sample data and demo accounts, include
`richfield.db` as well. Use a copy of the database for testing rather
than a database containing real or sensitive information.

## License

No license has been specified for this project. Ask the project owner
before reusing or redistributing it beyond the intended sharing purpose.
