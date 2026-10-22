
"""main.py — application entry point."""

import tkinter as tk
from tkinter import messagebox

from gui import BookingApp


def main():
    root = tk.Tk()

    try:
        BookingApp(root)
    except Exception as error:
        root.destroy()
        messagebox.showerror(
            "Startup error",
            f"The application could not start:\n{error}"
        )
        raise

    root.mainloop()


if __name__ == "__main__":
    main()
