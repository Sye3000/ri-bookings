
"""
gui.py
Rosebank International Booking System — graphical user interface.

Responsibilities:
- Display the login screen.
- Authenticate users through the database layer.
- Display a dashboard based on the user's role.
- Display available resources.

SQL statements remain in database.py.
"""

import tkinter as tk
from PIL import Image, ImageTk, ImageFilter, ImageDraw, ImageFont
from tkinter import ttk, messagebox
from pathlib import Path
from PIL import Image, ImageTk, ImageFilter, ImageOps

import database as db
import datetime as dt
import secrets
import string
import rules as booking_rules


# --------------------------------------------------
# Application colours
# --------------------------------------------------

ROYAL_BLUE = "#173B7A"
DARK_BLUE = "#102A56"
WHITE = "#FFFFFF"
GOLD = "#D4AF37"
LIGHT_GREY = "#F2F4F8"
DARK_TEXT = "#202B3C"


class BookingApp:
    """Main controller for the booking system GUI."""

    def __init__(self, root):
        self.root = root
        self.root.title("RI Bookings")
        self.root.geometry("900x600")
        self.root.minsize(700, 500)
        self.root.configure(bg=LIGHT_GREY)

        self.conn = db.initialise_database()
        self.current_user = None
        self.logo_image = self.load_logo()

        self.style = ttk.Style()
        self.style.configure(
            "Treeview",
            rowheight=30,
            font=("Arial", 10)
        )
        self.style.configure(
            "Treeview.Heading",
            font=("Arial", 10, "bold")
        )

        self.show_login()

        self.root.protocol("WM_DELETE_WINDOW", self.close_app)

    # --------------------------------------------------
    # Clear the current screen
    # --------------------------------------------------

    def load_logo(self, max_size=(150, 75)):
        """Load the RI logo while preserving its proportions."""
        logo_path = Path(__file__).resolve().parent / "RI Logo.jpeg"
        if not logo_path.exists():
            return None
        try:
            image = Image.open(logo_path)
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(image)
        except (OSError, AttributeError):
            return None

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    # --------------------------------------------------
    # Login screen
    # --------------------------------------------------

    def show_login(self):
        self.clear_screen()

        self._login_resize_job = None
        self._login_render_job = None
        self._login_canvas_image = None
        self._login_background_original = None
        self._login_window_items = {}

        self.login_canvas = tk.Canvas(
            self.root,
            highlightthickness=0,
            bd=0,
            background="#173B63"
        )
        self.login_canvas.pack(fill="both", expand=True)

        background_path = Path(__file__).resolve().parent / "Rosebank background.jpeg"

        try:
            self._login_background_original = Image.open(
                background_path
            ).convert("RGB")
        except Exception as exc:
            messagebox.showerror(
                "Background image error",
                f"Could not load Rosebank background.jpeg:\n{exc}"
            )
            self.login_canvas.destroy()
            return

        # The widgets are children of the canvas. Their positions are
        # recalculated relative to the card whenever the canvas is resized.
        self.username_entry = tk.Entry(
            self.login_canvas,
            font=("Arial", 12),
            bg="#DCEAF4",
            fg="#173B63",
            insertbackground="#173B63",
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground="#FFFFFF",
            highlightcolor="#FFFFFF"
        )

        self.password_entry = tk.Entry(
            self.login_canvas,
            show="*",
            font=("Arial", 12),
            bg="#DCEAF4",
            fg="#173B63",
            insertbackground="#173B63",
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground="#FFFFFF",
            highlightcolor="#FFFFFF"
        )

        self.login_button = tk.Button(
            self.login_canvas,
            text="SIGN IN  →",
            command=self.login,
            bg="#C6A45B",
            fg="#FFFFFF",
            activebackground="#A98543",
            activeforeground="#FFFFFF",
            font=("Arial", 11, "bold"),
            relief="flat",
            bd=0,
            cursor="hand2"
        )

        self._login_window_items = {
            "username": self.login_canvas.create_window(
                0, 0, window=self.username_entry, anchor="nw"
            ),
            "password": self.login_canvas.create_window(
                0, 0, window=self.password_entry, anchor="nw"
            ),
            "button": self.login_canvas.create_window(
                0, 0, window=self.login_button, anchor="nw"
            ),
        }

        self.login_canvas.bind(
            "<Configure>", self._schedule_login_render
        )

        self._render_login_background()
        self.username_entry.focus_set()
        self.root.bind("<Return>", self.handle_enter)

    def _schedule_login_render(self, event=None):
        # Debounce resize events so we render once after resizing settles.
        if self._login_resize_job is not None:
            try:
                self.root.after_cancel(self._login_resize_job)
            except tk.TclError:
                pass

        self._login_resize_job = self.root.after(
            140, self._render_login_background
        )

    def _render_login_background(self):
        if not hasattr(self, "login_canvas"):
            return
        if not self.login_canvas.winfo_exists():
            return
        if self._login_background_original is None:
            return

        self._login_resize_job = None

        width = max(self.login_canvas.winfo_width(), 1)
        height = max(self.login_canvas.winfo_height(), 1)

        # Scale to cover the entire window while preserving aspect ratio.
        original = self._login_background_original
        scale = max(width / original.width, height / original.height)
        resized = original.resize(
            (
                max(1, round(original.width * scale)),
                max(1, round(original.height * scale))
            ),
            Image.Resampling.LANCZOS
        )

        crop_x = (resized.width - width) // 2
        crop_y = (resized.height - height) // 2
        fitted = resized.crop(
            (crop_x, crop_y, crop_x + width, crop_y + height)
        )

        # The card adapts to smaller windows but remains centred.
        card_w = min(500, max(300, width - 32))
        card_h = min(470, max(390, height - 24))
        left = (width - card_w) // 2
        top = (height - card_h) // 2
        right = left + card_w
        bottom = top + card_h

        # Frosted glass is composited into the background image, not
        # represented by an opaque Tkinter Frame.
        blur_radius = max(8, min(14, round(width / 100)))
        region = fitted.crop((left, top, right, bottom))
        region = region.filter(
            ImageFilter.GaussianBlur(radius=blur_radius)
        ).convert("RGBA")

        tint = Image.new(
            "RGBA",
            (card_w, card_h),
            (190, 222, 245, 65)
        )
        glass = Image.alpha_composite(region, tint)

        mask = Image.new("L", (card_w, card_h), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (1, 1, card_w - 2, card_h - 2),
            radius=27,
            fill=255
        )

        canvas_image = fitted.convert("RGBA")
        canvas_image.paste(glass, (left, top), mask)

        draw = ImageDraw.Draw(canvas_image)
        draw.rounded_rectangle(
            (left, top, right - 1, bottom - 1),
            radius=27,
            outline=(255, 255, 255, 235),
            width=2
        )
        draw.line(
            (left + 35, top + 3, right - 35, top + 3),
            fill=(255, 255, 255, 220),
            width=2
        )

        # Draw text into the image itself. This avoids the coloured
        # background rectangles produced by Tkinter Label widgets.
        try:
            regular_font = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            bold_font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

            title_font = ImageFont.truetype(
                bold_font, max(15, min(21, card_w // 23))
            )
            subtitle_font = ImageFont.truetype(bold_font, 11)
            body_font = ImageFont.truetype(regular_font, 12)
            footer_font = ImageFont.truetype(regular_font, 10)
        except OSError:
            title_font = ImageFont.load_default()
            subtitle_font = body_font = footer_font = ImageFont.load_default()

        ink = (18, 59, 93, 255)
        muted = (66, 103, 131, 255)
        gold = (198, 164, 91, 255)
        white = (255, 255, 255, 240)

        def centered_text(text, y, font, fill):
            bounds = draw.textbbox((0, 0), text, font=font)
            text_w = bounds[2] - bounds[0]
            text_h = bounds[3] - bounds[1]
            x = left + (card_w - text_w) // 2
            draw.text((x, y), text, font=font, fill=fill)
            return text_h

        centered_text(
            "ROSEBANK INTERNATIONAL", top + 35, title_font, ink
        )
        centered_text(
            "BOOKING SYSTEM", top + 76, subtitle_font, gold
        )

        divider_y = top + 105
        draw.line(
            (left + 55, divider_y, right - 55, divider_y),
            fill=gold,
            width=2
        )

        centered_text(
            "Sign in to your account", top + 125, body_font, muted
        )

        # Reposition the actual input widgets relative to the card.
        inner_x = left + max(32, int(card_w * 0.11))
        inner_w = card_w - 2 * (inner_x - left)

        username_y = top + 170
        password_y = top + 230
        button_y = top + 300

        # Keep controls inside the glass if the window is short.
        available_bottom = bottom - 60
        button_y = min(button_y, available_bottom - 48)
        password_y = min(password_y, button_y - 60)
        username_y = min(username_y, password_y - 60)

        self.login_canvas.coords(
            self._login_window_items["username"], inner_x, username_y
        )
        self.login_canvas.itemconfigure(
            self._login_window_items["username"],
            width=inner_w, height=43
        )

        self.login_canvas.coords(
            self._login_window_items["password"], inner_x, password_y
        )
        self.login_canvas.itemconfigure(
            self._login_window_items["password"],
            width=inner_w, height=43
        )

        self.login_canvas.coords(
            self._login_window_items["button"], inner_x, button_y
        )
        self.login_canvas.itemconfigure(
            self._login_window_items["button"],
            width=inner_w, height=48
        )

        centered_text(
            "—  Authorised users only  —",
            bottom - 47,
            footer_font,
            white
        )

        self._login_canvas_image = ImageTk.PhotoImage(canvas_image)
        self.login_canvas.delete("background")
        self.login_canvas.create_image(
            0, 0,
            image=self._login_canvas_image,
            anchor="nw",
            tags=("background",)
        )
        self.login_canvas.tag_lower("background")
    def handle_enter(self, event=None):
        if self.current_user is None:
            self.login()

    # --------------------------------------------------
    # Authentication
    # --------------------------------------------------

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            messagebox.showwarning(
                "Missing information",
                "Enter both your username and password."
            )
            return

        row = self.conn.execute(
            """
            SELECT user_id, username, full_name,
                   password_hash, salt, role, campus_id,
                   must_change_password
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

        if row is None or not db.verify_password(
            password,
            row["password_hash"],
            row["salt"]
        ):
            messagebox.showerror(
                "Login failed",
                "Invalid username or password."
            )
            self.password_entry.delete(0, tk.END)
            self.password_entry.focus_set()
            return

        self.current_user = dict(row)
        if self.current_user.get("must_change_password", 0):
            self.show_force_password_change()
        else:
            self.show_dashboard()

    # --------------------------------------------------
    # Role-based dashboard
    # --------------------------------------------------

    def show_dashboard(self):
        self.clear_screen()
        self.root.unbind("<Return>")

        header = tk.Frame(
            self.root,
            bg=ROYAL_BLUE,
            padx=25,
            pady=18
        )
        header.pack(fill="x")

        if self.logo_image:
            tk.Label(
                header,
                image=self.logo_image,
                bg=ROYAL_BLUE
            ).pack(side="left", padx=(0, 14))

        tk.Label(
            header,
            text="RI Booking System",
            bg=ROYAL_BLUE,
            fg=WHITE,
            font=("Arial", 17, "bold")
        ).pack(side="left")

        tk.Button(
            header,
            text="Log out",
            command=self.logout,
            bg=GOLD,
            fg=DARK_BLUE,
            relief="flat",
            padx=15,
            pady=7,
            cursor="hand2"
        ).pack(side="right")

        role_labels = {
            "lecturer": "Lecturer",
            "campus_admin": "Campus Administrator",
            "system_operator": "System Operator"
        }

        role = self.current_user["role"]
        full_name = self.current_user["full_name"]

        tk.Label(
            self.root,
            text=f"Welcome, {full_name}",
            bg=LIGHT_GREY,
            fg=DARK_BLUE,
            font=("Arial", 20, "bold")
        ).pack(anchor="w", padx=30, pady=(25, 5))

        tk.Label(
            self.root,
            text=f"Role: {role_labels.get(role, role)}",
            bg=LIGHT_GREY,
            fg=DARK_TEXT,
            font=("Arial", 11)
        ).pack(anchor="w", padx=30, pady=(0, 15))

        self.content = tk.Frame(
            self.root,
            bg=WHITE,
            padx=20,
            pady=20
        )
        self.content.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=(0, 25)
        )

        if role == "lecturer":
            self.show_lecturer_dashboard()
        elif role == "campus_admin":
            self.show_admin_dashboard()
        elif role == "system_operator":
            self.show_operator_dashboard()
        else:
            messagebox.showerror(
                "Role error",
                "This account has an unsupported role."
            )
            self.logout()

    # --------------------------------------------------
    # Lecturer dashboard
    # --------------------------------------------------

    def show_lecturer_dashboard(self):
        for widget in self.content.winfo_children():
            widget.destroy()

        tk.Label(
            self.content,
            text="Lecturer Dashboard",
            bg=WHITE,
            fg=ROYAL_BLUE,
            font=("Arial", 16, "bold")
        ).pack(anchor="w", pady=(0, 8))

        tk.Label(
            self.content,
            text="Manage your campus resource bookings.",
            bg=WHITE,
            fg=DARK_TEXT
        ).pack(anchor="w", pady=(0, 18))

        actions = [
            ("Make a Booking", self.show_booking_form),
            ("Check Availability", self.show_booking_form),
            ("My Bookings", self.show_my_bookings),
            ("View Campus Resources", self.show_resources),
        ]

        for label, action in actions:
            tk.Button(
                self.content,
                text=label,
                command=action,
                bg=ROYAL_BLUE,
                fg=WHITE,
                activebackground=DARK_BLUE,
                activeforeground=WHITE,
                relief="flat",
                padx=16,
                pady=9,
                width=24
            ).pack(anchor="w", pady=5)

    # --------------------------------------------------
    # Booking form and availability
    # --------------------------------------------------

    def show_booking_form(self):
        for widget in self.content.winfo_children():
            widget.destroy()

        tk.Label(
            self.content,
            text="Make a Booking / Check Availability",
            bg=WHITE,
            fg=ROYAL_BLUE,
            font=("Arial", 15, "bold")
        ).pack(anchor="w", pady=(0, 12))

        form = tk.Frame(self.content, bg=WHITE)
        form.pack(anchor="w", fill="x")

        today = dt.date.today().isoformat()
        self.booking_date_var = tk.StringVar(value=today)
        self.booking_time_var = tk.StringVar(value="09:00")
        self.booking_duration_var = tk.StringVar(value="60")
        self.booking_resource_var = tk.StringVar(value="")

        fields = [
            ("Booking date (YYYY-MM-DD)", self.booking_date_var),
            ("Start time (HH:MM, 24-hour)", self.booking_time_var),
            ("Duration in minutes", self.booking_duration_var),
        ]

        for label_text, variable in fields:
            tk.Label(
                form,
                text=label_text,
                bg=WHITE,
                fg=DARK_TEXT
            ).pack(anchor="w", pady=(5, 2))

            tk.Entry(
                form,
                textvariable=variable,
                width=32
            ).pack(anchor="w")

        tk.Label(
            form,
            text="Available resource",
            bg=WHITE,
            fg=DARK_TEXT
        ).pack(anchor="w", pady=(8, 2))

        self.booking_resource_combo = ttk.Combobox(
            form,
            textvariable=self.booking_resource_var,
            state="readonly",
            width=55
        )
        self.booking_resource_combo.pack(anchor="w")

        self.booking_status_label = tk.Label(
            form,
            text="Check availability to load resources for your selected time.",
            bg=WHITE,
            fg="#6B7280",
            wraplength=650,
            justify="left"
        )
        self.booking_status_label.pack(anchor="w", pady=8)

        buttons = tk.Frame(form, bg=WHITE)
        buttons.pack(anchor="w", pady=6)

        tk.Button(
            buttons,
            text="Check Availability",
            command=self.check_booking_availability,
            bg=ROYAL_BLUE,
            fg=WHITE,
            relief="flat",
            padx=12,
            pady=8
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            buttons,
            text="Confirm Booking",
            command=self.submit_booking,
            bg=GOLD,
            fg="#202B3C",
            relief="flat",
            padx=12,
            pady=8
        ).pack(side="left")

        tk.Button(
            form,
            text="Back to Dashboard",
            command=self.show_lecturer_dashboard,
            bg=WHITE,
            fg=ROYAL_BLUE,
            relief="solid",
            padx=12,
            pady=7
        ).pack(anchor="w", pady=(8, 0))

        self.available_resource_ids = {}

    def _booking_inputs(self):
        booking_date = self.booking_date_var.get().strip()
        start_time = self.booking_time_var.get().strip()
        duration_text = self.booking_duration_var.get().strip()

        try:
            duration = int(duration_text)
        except ValueError:
            raise booking_rules.BookingError(
                "Duration must be a positive whole number."
            )

        if duration <= 0:
            raise booking_rules.BookingError(
                "Duration must be a positive whole number."
            )

        return booking_date, start_time, duration

    def check_booking_availability(self):
        try:
            booking_date, start_time, duration = self._booking_inputs()

            campus_id = self.current_user.get("campus_id")
            resources = booking_rules.get_available_resources(
                self.conn,
                booking_date,
                start_time,
                duration,
                campus_id=campus_id
            )

            old_selection = self.booking_resource_var.get()
            resource_ids = {}
            labels = []

            for resource in resources:
                label = (
                    f"{resource['resource_id']} - {resource['name']} | "
                    f"{resource['campus_name']} | "
                    f"{resource['resource_type']} | "
                    f"Capacity: {resource['capacity']}"
                )
                labels.append(label)
                resource_ids[label] = resource["resource_id"]

            self.available_resource_ids = resource_ids
            self.booking_resource_combo["values"] = labels

            if old_selection in resource_ids:
                self.booking_resource_var.set(old_selection)
            elif labels:
                self.booking_resource_var.set(labels[0])
            else:
                self.booking_resource_var.set("")

            if resources:
                self.booking_status_label.config(
                    text=f"{len(resources)} resource(s) available for this time.",
                    fg=ROYAL_BLUE
                )
            else:
                self.booking_status_label.config(
                    text="No resources are available for the selected time.",
                    fg="#B42318"
                )

        except booking_rules.BookingError as exc:
            messagebox.showerror("Availability Error", str(exc))
        except (ValueError, TypeError, KeyError) as exc:
            messagebox.showerror(
                "Availability Error",
                f"Could not check availability: {exc}"
            )

    def submit_booking(self):
        try:
            booking_date, start_time, duration = self._booking_inputs()
            selected = self.booking_resource_var.get()
            resource_id = self.available_resource_ids.get(selected)

            if resource_id is None:
                messagebox.showwarning(
                    "Select a Resource",
                    "Check availability and select a resource first."
                )
                return

            booking_id = booking_rules.create_booking(
                self.conn,
                self.current_user["user_id"],
                resource_id,
                booking_date,
                start_time,
                duration
            )

            messagebox.showinfo(
                "Booking Confirmed",
                f"Booking created successfully. Booking ID: {booking_id}"
            )
            self.show_my_bookings()

        except booking_rules.BookingError as exc:
            messagebox.showerror("Booking Error", str(exc))
        except (ValueError, TypeError, KeyError) as exc:
            messagebox.showerror(
                "Booking Error",
                f"Could not create the booking: {exc}"
            )

    # --------------------------------------------------
    # Lecturer booking history and cancellation
    # --------------------------------------------------

    def show_my_bookings(self):
        for widget in self.content.winfo_children():
            widget.destroy()

        tk.Label(
            self.content,
            text="My Bookings",
            bg=WHITE,
            fg=ROYAL_BLUE,
            font=("Arial", 16, "bold")
        ).pack(anchor="w", pady=(0, 12))

        columns = (
            "id", "campus", "resource", "date",
            "start", "duration", "status"
        )
        tree = ttk.Treeview(
            self.content,
            columns=columns,
            show="headings",
            height=10
        )

        headings = {
            "id": "Booking ID",
            "campus": "Campus",
            "resource": "Resource",
            "date": "Date",
            "start": "Start",
            "duration": "Minutes",
            "status": "Status"
        }

        widths = {
            "id": 80,
            "campus": 105,
            "resource": 150,
            "date": 100,
            "start": 75,
            "duration": 75,
            "status": 90
        }

        for column in columns:
            tree.heading(column, text=headings[column])
            tree.column(column, width=widths[column], anchor="w")

        tree.pack(fill="both", expand=True)

        rows = booking_rules.get_user_bookings(
            self.conn,
            self.current_user["user_id"]
        )

        for row in rows:
            tree.insert(
                "",
                "end",
                values=(
                    row["booking_id"],
                    row["campus_name"],
                    row["resource_name"],
                    row["booking_date"],
                    row["start_time"],
                    row["duration_minutes"],
                    row["status"]
                )
            )

        buttons = tk.Frame(self.content, bg=WHITE)
        buttons.pack(anchor="w", pady=(12, 0))

        def cancel_selected():
            selection = tree.selection()

            if not selection:
                messagebox.showwarning(
                    "Select a Booking",
                    "Select a booking from the list first."
                )
                return

            values = tree.item(selection[0], "values")
            booking_id = int(values[0])
            status = values[6]

            if status != "active":
                messagebox.showwarning(
                    "Cannot Cancel",
                    "Only active bookings can be cancelled."
                )
                return

            confirmed = messagebox.askyesno(
                "Confirm Cancellation",
                f"Cancel booking {booking_id}?"
            )
            if not confirmed:
                return

            try:
                booking_rules.cancel_booking(
                    self.conn,
                    booking_id,
                    user_id=self.current_user["user_id"]
                )
                messagebox.showinfo(
                    "Booking Cancelled",
                    f"Booking {booking_id} has been cancelled."
                )
                self.show_my_bookings()
            except booking_rules.BookingError as exc:
                messagebox.showerror("Cancellation Error", str(exc))

        tk.Button(
            buttons,
            text="Cancel Selected Booking",
            command=cancel_selected,
            bg=ROYAL_BLUE,
            fg=WHITE,
            relief="flat",
            padx=12,
            pady=8
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            buttons,
            text="Back to Dashboard",
            command=self.show_lecturer_dashboard,
            bg=WHITE,
            fg=ROYAL_BLUE,
            relief="solid",
            padx=12,
            pady=8
        ).pack(side="left")

    # --------------------------------------------------
    # Campus administrator dashboard
    # --------------------------------------------------

    def show_admin_dashboard(self):
        campus_id = self.current_user["campus_id"]

        campus = self.conn.execute(
            "SELECT name FROM campuses WHERE campus_id = ?",
            (campus_id,)
        ).fetchone()

        if campus is None:
            messagebox.showerror(
                "Campus Error",
                "Your account is not assigned to a valid campus."
            )
            return

        resource_count = self.conn.execute(
            "SELECT COUNT(*) FROM resources WHERE campus_id = ?",
            (campus_id,)
        ).fetchone()[0]

        user_count = self.conn.execute(
            "SELECT COUNT(*) FROM users WHERE campus_id = ?",
            (campus_id,)
        ).fetchone()[0]

        booking_count = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM bookings b
            JOIN resources r ON b.resource_id = r.resource_id
            WHERE r.campus_id = ?
            """,
            (campus_id,)
        ).fetchone()[0]

        tk.Label(
            self.content,
            text="Campus Administrator Dashboard",
            bg=WHITE,
            fg=ROYAL_BLUE,
            font=("Arial", 18, "bold")
        ).pack(anchor="w", pady=(0, 5))

        tk.Label(
            self.content,
            text=f"Campus: {campus['name']}",
            bg=WHITE,
            fg=DARK_TEXT,
            font=("Arial", 12)
        ).pack(anchor="w", pady=(0, 15))

        tk.Label(
            self.content,
            text="Campus Overview",
            bg=WHITE,
            fg=ROYAL_BLUE,
            font=("Arial", 14, "bold")
        ).pack(anchor="w", pady=(0, 10))

        summary = (
            f"Resources: {resource_count}\n"
            f"Campus users: {user_count}\n"
            f"Total bookings: {booking_count}"
        )

        tk.Label(
            self.content,
            text=summary,
            bg=WHITE,
            fg=DARK_TEXT,
            font=("Arial", 12),
            justify="left",
            padx=15,
            pady=12,
            relief="solid",
            bd=1
        ).pack(anchor="w", fill="x", pady=(0, 18))

        buttons = tk.Frame(self.content, bg=WHITE)
        buttons.pack(anchor="w")

        tk.Button(
            buttons,
            text="View Campus Resources",
            command=lambda: self.show_resources(campus_id=campus_id),
            bg=ROYAL_BLUE,
            fg=WHITE,
            relief="flat",
            padx=15,
            pady=10
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            buttons,
            text="Manage Bookings",
            command=self.show_admin_bookings,
            bg=ROYAL_BLUE,
            fg=WHITE,
            relief="flat",
            padx=15,
            pady=10
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            buttons,
            text="Manage Campus Users",
            command=self.show_admin_users,
            bg=ROYAL_BLUE,
            fg=WHITE,
            relief="flat",
            padx=15,
            pady=10
        ).pack(side="left")

    def show_admin_bookings(self):
        for widget in self.content.winfo_children():
            widget.destroy()

        campus_id = self.current_user["campus_id"]

        tk.Label(
            self.content,
            text="Manage Campus Bookings",
            bg=WHITE,
            fg=ROYAL_BLUE,
            font=("Arial", 16, "bold")
        ).pack(anchor="w", pady=(0, 12))

        columns = (
            "id", "lecturer", "resource", "date",
            "start", "duration", "status"
        )

        tree = ttk.Treeview(
            self.content,
            columns=columns,
            show="headings",
            height=12
        )

        headings = {
            "id": "Booking ID",
            "lecturer": "Booked By",
            "resource": "Resource",
            "date": "Date",
            "start": "Start",
            "duration": "Minutes",
            "status": "Status"
        }

        widths = {
            "id": 80,
            "lecturer": 150,
            "resource": 150,
            "date": 100,
            "start": 75,
            "duration": 75,
            "status": 90
        }

        for column in columns:
            tree.heading(column, text=headings[column])
            tree.column(column, width=widths[column], anchor="w")

        tree.pack(fill="both", expand=True)

        def load_bookings():
            for item in tree.get_children():
                tree.delete(item)

            rows = self.conn.execute(
                """
                SELECT b.booking_id, u.full_name, r.name AS resource_name,
                       b.booking_date, b.start_time,
                       b.duration_minutes, b.status
                FROM bookings b
                JOIN users u ON b.user_id = u.user_id
                JOIN resources r ON b.resource_id = r.resource_id
                WHERE r.campus_id = ?
                ORDER BY b.booking_date DESC, b.start_time
                """,
                (campus_id,)
            ).fetchall()

            for row in rows:
                tree.insert(
                    "",
                    "end",
                    values=(
                        row["booking_id"],
                        row["full_name"],
                        row["resource_name"],
                        row["booking_date"],
                        row["start_time"],
                        row["duration_minutes"],
                        row["status"]
                    )
                )

        def cancel_selected():
            selection = tree.selection()

            if not selection:
                messagebox.showwarning(
                    "Select a Booking",
                    "Select a booking from the list first."
                )
                return

            values = tree.item(selection[0], "values")
            booking_id = int(values[0])

            if values[6] != "active":
                messagebox.showwarning(
                    "Cannot Cancel",
                    "Only active bookings can be cancelled."
                )
                return

            confirmed = messagebox.askyesno(
                "Confirm Cancellation",
                f"Cancel booking {booking_id}?"
            )

            if not confirmed:
                return

            # Verify campus ownership before cancelling.
            booking = self.conn.execute(
                """
                SELECT b.booking_id
                FROM bookings b
                JOIN resources r ON b.resource_id = r.resource_id
                WHERE b.booking_id = ?
                  AND r.campus_id = ?
                  AND b.status = 'active'
                """,
                (booking_id, campus_id)
            ).fetchone()

            if booking is None:
                messagebox.showerror(
                    "Booking Error",
                    "The booking is no longer active or does not "
                    "belong to your campus."
                )
                load_bookings()
                return

            try:
                booking_rules.cancel_booking(self.conn, booking_id)
                messagebox.showinfo(
                    "Booking Cancelled",
                    f"Booking {booking_id} has been cancelled."
                )
                load_bookings()
            except booking_rules.BookingError as exc:
                messagebox.showerror("Cancellation Error", str(exc))

        buttons = tk.Frame(self.content, bg=WHITE)
        buttons.pack(anchor="w", pady=(12, 0))

        tk.Button(
            buttons,
            text="Cancel Selected Booking",
            command=cancel_selected,
            bg=ROYAL_BLUE,
            fg=WHITE,
            relief="flat",
            padx=12,
            pady=8
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            buttons,
            text="Refresh",
            command=load_bookings,
            bg=WHITE,
            fg=ROYAL_BLUE,
            relief="solid",
            padx=12,
            pady=8
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            buttons,
            text="Back to Dashboard",
            command=self.show_admin_dashboard,
            bg=WHITE,
            fg=ROYAL_BLUE,
            relief="solid",
            padx=12,
            pady=8
        ).pack(side="left")

        load_bookings()

    # --------------------------------------------------

    # --------------------------------------------------
    # Lecturer registration and first-login password change
    # --------------------------------------------------

    def _make_temporary_password(self):
        """Generate a random temporary password with mixed character classes."""
        alphabet = string.ascii_letters + string.digits + "!@#$%*-_"
        while True:
            password = "".join(secrets.choice(alphabet) for _ in range(16))
            if (
                any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
                and any(c in "!@#$%*-_" for c in password)
            ):
                return password

    def show_register_lecturer(self):
        if (
            not self.current_user
            or self.current_user.get("role") != "campus_admin"
            or self.current_user.get("campus_id") is None
        ):
            messagebox.showerror(
                "Access Denied",
                "Only a campus administrator can register lecturers."
            )
            return

        campus_id = self.current_user["campus_id"]
        campus = self.conn.execute(
            "SELECT name FROM campuses WHERE campus_id = ?", (campus_id,)
        ).fetchone()
        if campus is None:
            messagebox.showerror("Campus Error", "Your campus is invalid.")
            return

        for widget in self.content.winfo_children():
            widget.destroy()

        tk.Label(
            self.content, text="Register Lecturer", bg=WHITE, fg=ROYAL_BLUE,
            font=("Arial", 16, "bold")
        ).pack(anchor="w", pady=(0, 5))
        tk.Label(
            self.content, text=f"Campus: {campus['name']}", bg=WHITE,
            fg=DARK_TEXT, font=("Arial", 11)
        ).pack(anchor="w", pady=(0, 12))

        form = tk.Frame(self.content, bg=WHITE)
        form.pack(anchor="w", fill="x")
        entries = {}

        for label_text, key in (
            ("Lecturer full name", "full_name"),
            ("Username", "username"),
            ("Email address", "email"),
        ):
            tk.Label(
                form, text=label_text, bg=WHITE, fg=DARK_TEXT
            ).pack(anchor="w", pady=(6, 2))
            entry = ttk.Entry(form, width=42)
            entry.pack(anchor="w", ipady=3)
            entries[key] = entry

        tk.Label(
            form,
            text="A temporary password will be generated after registration.",
            bg=WHITE, fg="#6B7280", wraplength=620, justify="left"
        ).pack(anchor="w", pady=12)

        def save_lecturer():
            full_name = entries["full_name"].get().strip()
            username = entries["username"].get().strip()
            email = entries["email"].get().strip()

            if not all((full_name, username, email)):
                messagebox.showwarning(
                    "Missing Information", "Complete all three fields."
                )
                return
            if len(username) < 3 or any(c.isspace() for c in username):
                messagebox.showwarning(
                    "Invalid Username",
                    "Username must be at least 3 characters and contain no spaces."
                )
                return
            if self.current_user.get("role") != "campus_admin":
                messagebox.showerror("Access Denied", "Permission denied.")
                return
            if self.current_user.get("campus_id") != campus_id:
                messagebox.showerror(
                    "Access Denied", "Campus assignment changed. Try again."
                )
                return

            temporary_password = self._make_temporary_password()
            try:
                user_id = db.create_lecturer(
                    self.conn, full_name, username, email,
                    campus_id, temporary_password
                )
            except ValueError as exc:
                messagebox.showerror("Registration Error", str(exc))
                return
            except Exception as exc:
                self.conn.rollback()
                messagebox.showerror(
                    "Registration Error",
                    f"The lecturer could not be registered: {exc}"
                )
                return

            self.show_admin_users()
            messagebox.showinfo(
                "Lecturer Registered",
                f"Lecturer: {full_name}\n"
                f"Username: {username}\n"
                f"Temporary password: {temporary_password}\n\n"
                "Copy this password now and pass it securely to the lecturer. "
                "It will not be shown again. The lecturer must change it "
                "before accessing the system."
            )

        buttons = tk.Frame(self.content, bg=WHITE)
        buttons.pack(anchor="w", pady=(14, 0))
        tk.Button(
            buttons, text="Create Lecturer", command=save_lecturer,
            bg=ROYAL_BLUE, fg=WHITE, relief="flat", padx=14, pady=8
        ).pack(side="left", padx=(0, 8))
        tk.Button(
            buttons, text="Cancel", command=self.show_admin_users,
            bg=WHITE, fg=ROYAL_BLUE, relief="solid", padx=14, pady=8
        ).pack(side="left")

    def show_force_password_change(self):
        """Require newly registered lecturers to change their temporary password."""
        self.clear_screen()
        self.root.unbind("<Return>")

        panel = tk.Frame(self.root, bg=WHITE, padx=35, pady=30)
        panel.place(relx=0.5, rely=0.5, anchor="center", width=520, height=440)

        tk.Label(
            panel, text="Change Temporary Password", bg=WHITE,
            fg=ROYAL_BLUE, font=("Arial", 19, "bold")
        ).pack(anchor="w", pady=(0, 10))
        tk.Label(
            panel,
            text="Choose a new password before continuing. Use at least "
                 "12 characters, including uppercase, lowercase, a number "
                 "and a symbol.",
            bg=WHITE, fg=DARK_TEXT, wraplength=440, justify="left"
        ).pack(anchor="w", pady=(0, 18))

        tk.Label(panel, text="New password", bg=WHITE, fg=DARK_TEXT).pack(anchor="w")
        self.new_password_entry = ttk.Entry(panel, show="*", width=42)
        self.new_password_entry.pack(anchor="w", fill="x", pady=(4, 12))
        tk.Label(panel, text="Confirm new password", bg=WHITE, fg=DARK_TEXT).pack(anchor="w")
        self.confirm_password_entry = ttk.Entry(panel, show="*", width=42)
        self.confirm_password_entry.pack(anchor="w", fill="x", pady=(4, 18))

        tk.Button(
            panel, text="Save New Password", command=self.save_new_password,
            bg=ROYAL_BLUE, fg=WHITE, relief="flat", padx=14, pady=10
        ).pack(fill="x")

    def save_new_password(self):
        password = self.new_password_entry.get()
        confirmation = self.confirm_password_entry.get()

        if password != confirmation:
            messagebox.showerror("Password Error", "The passwords do not match.")
            return
        if len(password) < 12:
            messagebox.showerror(
                "Password Error", "Use at least 12 characters."
            )
            return
        if not any(c.islower() for c in password):
            messagebox.showerror(
                "Password Error", "Include at least one lowercase letter."
            )
            return
        if not any(c.isupper() for c in password):
            messagebox.showerror(
                "Password Error", "Include at least one uppercase letter."
            )
            return
        if not any(c.isdigit() for c in password):
            messagebox.showerror(
                "Password Error", "Include at least one number."
            )
            return
        if not any(not c.isalnum() for c in password):
            messagebox.showerror(
                "Password Error", "Include at least one symbol."
            )
            return

        password_hash, salt = db.hash_password(password)
        self.conn.execute(
            """
            UPDATE users
            SET password_hash = ?, salt = ?, must_change_password = 0
            WHERE user_id = ? AND must_change_password = 1
            """,
            (password_hash, salt, self.current_user["user_id"])
        )
        self.conn.commit()
        self.current_user["must_change_password"] = 0
        self.show_dashboard()

    def show_admin_users(self):
        for widget in self.content.winfo_children():
            widget.destroy()

        campus_id = self.current_user["campus_id"]

        campus = self.conn.execute(
            "SELECT name FROM campuses WHERE campus_id = ?",
            (campus_id,)
        ).fetchone()

        if campus is None:
            messagebox.showerror(
                "Campus Error",
                "Your account is not assigned to a valid campus."
            )
            self.show_admin_dashboard()
            return

        tk.Label(
            self.content,
            text="Manage Campus Users",
            bg=WHITE,
            fg=ROYAL_BLUE,
            font=("Arial", 16, "bold")
        ).pack(anchor="w", pady=(0, 5))

        tk.Label(
            self.content,
            text=f"Campus: {campus['name']}",
            bg=WHITE,
            fg=DARK_TEXT,
            font=("Arial", 11)
        ).pack(anchor="w", pady=(0, 12))

        columns = ("id", "username", "full_name", "role")

        tree = ttk.Treeview(
            self.content,
            columns=columns,
            show="headings",
            height=12
        )

        headings = {
            "id": "User ID",
            "username": "Username",
            "full_name": "Full Name",
            "role": "Role"
        }

        widths = {
            "id": 80,
            "username": 150,
            "full_name": 250,
            "role": 160
        }

        for column in columns:
            tree.heading(column, text=headings[column])
            tree.column(column, width=widths[column], anchor="w")

        tree.pack(fill="both", expand=True)

        def load_users():
            for item in tree.get_children():
                tree.delete(item)

            rows = self.conn.execute(
                """
                SELECT user_id, username, full_name, role
                FROM users
                WHERE campus_id = ?
                ORDER BY role, full_name
                """,
                (campus_id,)
            ).fetchall()

            for row in rows:
                tree.insert(
                    "",
                    "end",
                    values=(
                        row["user_id"],
                        row["username"],
                        row["full_name"],
                        row["role"]
                    )
                )

        buttons = tk.Frame(self.content, bg=WHITE)
        buttons.pack(anchor="w", pady=(12, 0))

        tk.Button(
            buttons,
            text="Register Lecturer",
            command=self.show_register_lecturer,
            bg=ROYAL_BLUE,
            fg=WHITE,
            relief="flat",
            padx=12,
            pady=8
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            buttons,
            text="Refresh",
            command=load_users,
            bg=WHITE,
            fg=ROYAL_BLUE,
            relief="solid",
            padx=12,
            pady=8
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            buttons,
            text="Back to Dashboard",
            command=self.show_admin_dashboard,
            bg=WHITE,
            fg=ROYAL_BLUE,
            relief="solid",
            padx=12,
            pady=8
        ).pack(side="left")

        load_users()

    # System operator dashboard
    # --------------------------------------------------

    def show_operator_dashboard(self):
        tk.Label(
            self.content,
            text="System Operator Dashboard",
            bg=WHITE,
            fg=ROYAL_BLUE,
            font=("Arial", 16, "bold")
        ).pack(anchor="w")

        counts = {}

        for table in ("campuses", "users", "resources", "bookings"):
            counts[table] = self.conn.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]

        summary = (
            f"Campuses: {counts['campuses']}\n"
            f"Registered users: {counts['users']}\n"
            f"Resources: {counts['resources']}\n"
            f"Bookings: {counts['bookings']}"
        )

        tk.Label(
            self.content,
            text=summary,
            bg=WHITE,
            fg=DARK_TEXT,
            font=("Arial", 12),
            justify="left"
        ).pack(anchor="w", pady=15)

        tk.Button(
            self.content,
            text="View All Resources",
            command=self.show_resources,
            bg=ROYAL_BLUE,
            fg=WHITE,
            relief="flat",
            padx=15,
            pady=10
        ).pack(anchor="w")

    # --------------------------------------------------
    # Resource listing
    # --------------------------------------------------

    def show_resources(self, campus_id=None):
        for widget in self.content.winfo_children():
            widget.destroy()

        tk.Label(
            self.content,
            text="Campus Resources",
            bg=WHITE,
            fg=ROYAL_BLUE,
            font=("Arial", 16, "bold")
        ).pack(anchor="w", pady=(0, 12))

        columns = ("id", "campus", "name", "type", "capacity")

        tree = ttk.Treeview(
            self.content,
            columns=columns,
            show="headings"
        )

        headings = {
            "id": "Resource ID",
            "campus": "Campus",
            "name": "Resource",
            "type": "Type",
            "capacity": "Capacity"
        }

        for column, heading in headings.items():
            tree.heading(column, text=heading)

        tree.column("id", width=110)
        tree.column("campus", width=90)
        tree.column("name", width=180)
        tree.column("type", width=100)
        tree.column("capacity", width=80)

        tree.pack(fill="both", expand=True)

        sql = """
            SELECT r.resource_id, c.name AS campus_name,
                   r.name, r.resource_type, r.capacity
            FROM resources AS r
            JOIN campuses AS c ON r.campus_id = c.campus_id
        """
        params = ()

        if campus_id is not None:
            sql += " WHERE r.campus_id = ?"
            params = (campus_id,)

        sql += " ORDER BY c.name, r.resource_id"

        rows = self.conn.execute(sql, params).fetchall()

        for row in rows:
            tree.insert(
                "",
                "end",
                values=(
                    row["resource_id"],
                    row["campus_name"],
                    row["name"],
                    row["resource_type"],
                    row["capacity"]
                )
            )

        buttons = tk.Frame(self.content, bg=WHITE)
        buttons.pack(anchor="w", pady=(12, 0))

        if (
            self.current_user
            and self.current_user["role"] == "campus_admin"
            and campus_id == self.current_user["campus_id"]
        ):
            tk.Button(
                buttons,
                text="Add Resource",
                command=self.show_add_resource_form,
                bg=ROYAL_BLUE,
                fg=WHITE,
                relief="flat",
                padx=15,
                pady=8
            ).pack(side="left", padx=(0, 10))

        tk.Button(
            buttons,
            text="Back to Dashboard",
            command=self.show_dashboard,
            bg=WHITE,
            fg=ROYAL_BLUE,
            relief="solid",
            padx=15,
            pady=8
        ).pack(side="left")

    def show_add_resource_form(self):
        if (
            not self.current_user
            or self.current_user["role"] != "campus_admin"
            or self.current_user["campus_id"] is None
        ):
            messagebox.showerror(
                "Access Denied",
                "Only a campus administrator can add resources."
            )
            return

        campus_id = self.current_user["campus_id"]

        campus = self.conn.execute(
            "SELECT name FROM campuses WHERE campus_id = ?",
            (campus_id,)
        ).fetchone()

        if campus is None:
            messagebox.showerror(
                "Campus Error",
                "Your account is not assigned to a valid campus."
            )
            return

        for widget in self.content.winfo_children():
            widget.destroy()

        tk.Label(
            self.content,
            text="Add Campus Resource",
            bg=WHITE,
            fg=ROYAL_BLUE,
            font=("Arial", 16, "bold")
        ).pack(anchor="w", pady=(0, 5))

        tk.Label(
            self.content,
            text=f"Campus: {campus['name']}",
            bg=WHITE,
            fg=DARK_TEXT,
            font=("Arial", 11)
        ).pack(anchor="w", pady=(0, 15))

        form = tk.Frame(self.content, bg=WHITE)
        form.pack(anchor="w", fill="x")

        fields = [
            ("Resource ID", "id"),
            ("Resource Name", "name"),
            ("Resource Type", "type"),
            ("Capacity", "capacity"),
        ]

        entries = {}

        for label_text, key in fields:
            tk.Label(
                form,
                text=label_text,
                bg=WHITE,
                fg=DARK_TEXT,
                font=("Arial", 11)
            ).pack(anchor="w", pady=(6, 2))

            entry = tk.Entry(form, width=40, font=("Arial", 11))
            entry.pack(anchor="w", ipady=4)
            entries[key] = entry

        tk.Label(
            form,
            text="Examples: A-LAB-02, Computer Lab 2, Lab, 30",
            bg=WHITE,
            fg="gray",
            font=("Arial", 9)
        ).pack(anchor="w", pady=(8, 12))

        def save_resource():
            resource_id = entries["id"].get().strip().upper()
            name = entries["name"].get().strip()
            resource_type = entries["type"].get().strip()
            capacity_text = entries["capacity"].get().strip()

            if not all((resource_id, name, resource_type, capacity_text)):
                messagebox.showwarning(
                    "Missing Information",
                    "Complete all fields before saving."
                )
                return

            try:
                capacity = int(capacity_text)
                if capacity <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning(
                    "Invalid Capacity",
                    "Capacity must be a whole number greater than zero."
                )
                return

            # Verify campus ownership again before inserting.
            if self.current_user["campus_id"] != campus_id:
                messagebox.showerror(
                    "Access Denied",
                    "You cannot add resources to another campus."
                )
                return

            try:
                self.conn.execute(
                    """
                    INSERT INTO resources
                        (resource_id, campus_id, name, resource_type, capacity)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        resource_id,
                        campus_id,
                        name,
                        resource_type,
                        capacity
                    )
                )
                self.conn.commit()

            except Exception as exc:
                self.conn.rollback()
                if "UNIQUE constraint failed: resources.resource_id" in str(exc):
                    messagebox.showerror(
                        "Duplicate Resource ID",
                        "That resource ID already exists. Choose another ID."
                    )
                else:
                    messagebox.showerror(
                        "Save Error",
                        f"The resource could not be saved.\n{exc}"
                    )
                return

            messagebox.showinfo(
                "Resource Added",
                f"{name} was added to {campus['name']}."
            )
            self.show_resources(campus_id=campus_id)

        buttons = tk.Frame(self.content, bg=WHITE)
        buttons.pack(anchor="w", pady=(16, 0))

        tk.Button(
            buttons,
            text="Save Resource",
            command=save_resource,
            bg=ROYAL_BLUE,
            fg=WHITE,
            relief="flat",
            padx=15,
            pady=8
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            buttons,
            text="Cancel",
            command=lambda: self.show_resources(campus_id=campus_id),
            bg=WHITE,
            fg=ROYAL_BLUE,
            relief="solid",
            padx=15,
            pady=8
        ).pack(side="left")

    # --------------------------------------------------
    # Logout and shutdown
    # --------------------------------------------------

    def logout(self):
        self.current_user = None
        self.root.unbind("<Return>")
        self.show_login()

    def close_app(self):
        if self.conn:
            self.conn.close()
        self.root.destroy()
