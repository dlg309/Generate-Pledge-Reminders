"""Simple Windows desktop front end for pledge reminder generation."""

import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from generate_pledge_reminders import (
    TEMPLATE_PDF,
    find_asset,
    generate_batch,
    load_rows,
)


class ReminderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Pledge Reminders")
        root.geometry("700x390")
        root.minsize(600, 350)

        self.csv_var = tk.StringVar()
        self.save_var = tk.StringVar(value=str(Path.home() / "Documents"))
        self.assets_var = tk.StringVar(value="Select a donor CSV to see its signature images.")
        self.status_var = tk.StringVar(value="Ready")
        self.last_output: Path | None = None

        frame = ttk.Frame(root, padding=18)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Donor CSV").grid(row=0, column=0, sticky="w", pady=7)
        ttk.Entry(frame, textvariable=self.csv_var).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(frame, text="Browse…", command=self.choose_csv).grid(row=0, column=2)

        ttk.Label(frame, text="Save results in").grid(row=1, column=0, sticky="w", pady=7)
        ttk.Entry(frame, textvariable=self.save_var).grid(row=1, column=1, sticky="ew", padx=8)
        ttk.Button(frame, text="Browse…", command=self.choose_destination).grid(row=1, column=2)

        ttk.Label(frame, text="Template PDF").grid(row=2, column=0, sticky="nw", pady=7)
        find_asset(TEMPLATE_PDF)
        ttk.Label(frame, text=f"{TEMPLATE_PDF} (included with app)", wraplength=490).grid(
            row=2, column=1, columnspan=2, sticky="w"
        )

        ttk.Label(frame, text="Signature images").grid(row=3, column=0, sticky="nw", pady=7)
        ttk.Label(frame, textvariable=self.assets_var, wraplength=490, justify="left").grid(
            row=3, column=1, columnspan=2, sticky="w", pady=7
        )

        ttk.Separator(frame).grid(row=4, column=0, columnspan=3, sticky="ew", pady=18)
        self.generate_button = ttk.Button(frame, text="Generate", command=self.start_generation)
        self.generate_button.grid(row=5, column=0, sticky="w")
        self.open_button = ttk.Button(frame, text="Open output folder", command=self.open_output)
        self.open_button.grid(row=5, column=1, sticky="w", padx=8)
        self.open_button.state(["disabled"])
        ttk.Label(frame, textvariable=self.status_var, wraplength=620).grid(
            row=6, column=0, columnspan=3, sticky="w", pady=16
        )
        ttk.Label(frame, text="Created by @dlg309").grid(
            row=7, column=0, columnspan=3, sticky="w"
        )

        self.csv_var.trace_add("write", lambda *_: self.refresh_assets())

    def choose_csv(self):
        selected = filedialog.askopenfilename(title="Choose donor CSV", filetypes=[("CSV files", "*.csv")])
        if selected:
            self.csv_var.set(selected)

    def choose_destination(self):
        selected = filedialog.askdirectory(title="Choose where to save reminder folders")
        if selected:
            self.save_var.set(selected)

    def refresh_assets(self):
        raw = self.csv_var.get().strip().strip('"')
        if not raw:
            self.assets_var.set("Select a donor CSV to see its signature images.")
            return
        csv_path = Path(raw)
        if not csv_path.is_file():
            self.assets_var.set("CSV file not found.")
            return
        try:
            rows = load_rows(csv_path)
            names = sorted({row.get("Signatory_Signature_Image", "").strip() for row in rows})
            resolved = []
            for name in names:
                if not name:
                    resolved.append("(no signature)")
                    continue
                found = find_asset(name, csv_path)
                source = "beside CSV" if found.parent == csv_path.parent else "included with app"
                resolved.append(f"{name} ({source})")
            self.assets_var.set(f"{len(rows)} donors\n" + "\n".join(resolved))
        except Exception as exc:
            self.assets_var.set(f"Cannot read CSV or signature: {exc}")

    def start_generation(self):
        csv_path = Path(self.csv_var.get().strip().strip('"'))
        destination = Path(self.save_var.get().strip().strip('"'))
        if not csv_path.is_file():
            messagebox.showerror("Missing CSV", "Select an existing donor CSV file.")
            return
        if not destination.is_dir():
            messagebox.showerror("Missing save folder", "Select an existing folder for the results.")
            return
        self.status_var.set("Generating reminders…")
        self.generate_button.state(["disabled"])
        self.root.config(cursor="watch")
        thread = threading.Thread(target=self.generate, args=(csv_path, destination), daemon=True)
        thread.start()

    def generate(self, csv_path: Path, destination: Path):
        try:
            output = generate_batch(csv_path, destination)
        except Exception as exc:
            self.root.after(0, self.finish_error, str(exc))
        else:
            self.root.after(0, self.finish_success, output)

    def finish_error(self, detail: str):
        self.root.config(cursor="")
        self.generate_button.state(["!disabled"])
        self.status_var.set("Generation failed. See the error message.")
        messagebox.showerror("Pledge reminders", detail)

    def finish_success(self, output: Path):
        self.root.config(cursor="")
        self.generate_button.state(["!disabled"])
        self.last_output = output
        self.open_button.state(["!disabled"])
        self.status_var.set(f"Done. Files saved in {output}")
        messagebox.showinfo("Pledge reminders", f"Reminders created in:\n{output}")

    def open_output(self):
        if self.last_output:
            os.startfile(self.last_output)


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--smoke-test":
        generate_batch(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        window = tk.Tk()
        ReminderApp(window)
        window.mainloop()
