
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import csv
from datetime import date

DB = "students.db"
DEPARTMENTS = [
    "Computer Science", "Software Engineering",
    "Information Technology", "Electrical Engineering",
    "Mechanical Engineering", "Medical", "Business", "Other"
]

LIGHT = {
    "bg": "#F1F5F9", "card": "#FFFFFF",
    "fg": "#1E293B", "muted": "#64748B",
    "sidebar": "#172554", "input": "#FFFFFF"
}
DARK = {
    "bg": "#0F172A", "card": "#1E293B",
    "fg": "#F1F5F9", "muted": "#94A3B8",
    "sidebar": "#020617", "input": "#334155"
}

theme = LIGHT
selected_id = None


# DATABASE
def connect():
    return sqlite3.connect(DB, timeout=10)


def setup_db():
    with connect() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                roll_no TEXT UNIQUE NOT NULL,
                department TEXT NOT NULL,
                email TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        columns = {
            row[1] for row in con.execute(
                "PRAGMA table_info(students)"
            )
        }
        for col in ("email", "phone", "created_at"):
            if col not in columns:
                con.execute(
                    f"ALTER TABLE students ADD COLUMN {col} TEXT DEFAULT ''"
                )


# HELPERS
def button(parent, text, command, color="#2563EB"):
    return tk.Button(
        parent, text=text, command=command,
        bg=color, fg="white", activeforeground="white",
        activebackground=color, relief="flat",
        cursor="hand2", padx=12, pady=7,
        font=("Segoe UI", 9, "bold")
    )


def notify_error(error):
    messagebox.showerror("Error", str(error))


def form_data():
    return tuple(v.get().strip() for v in (
        name_var, roll_var, dept_var, email_var, phone_var
    ))


def validate(data):
    name, roll, dept, email, phone = data

    if not name or not roll or not dept:
        messagebox.showwarning(
            "Required", "Name, roll number and department are required."
        )
        return False

    if email and (
        "@" not in email or "." not in email.rsplit("@", 1)[-1]
    ):
        messagebox.showwarning("Invalid Email", "Enter a valid email.")
        return False

    if len(name) > 100 or len(roll) > 50:
        messagebox.showwarning("Invalid Input", "Input is too long.")
        return False

    return True


def clear_form():
    global selected_id
    selected_id = None

    for var in (name_var, roll_var, dept_var, email_var, phone_var):
        var.set("")

    if table.selection():
        table.selection_remove(table.selection())

    form_title.config(text="Add New Student")
    save_btn.config(text="Add Student", command=add_student)


# CRUD
def add_student():
    data = form_data()
    if not validate(data):
        return

    try:
        with connect() as con:
            con.execute("""
                INSERT INTO students
                (name, roll_no, department, email, phone)
                VALUES (?, ?, ?, ?, ?)
            """, data)

        clear_form()
        refresh()
        messagebox.showinfo("Success", "Student added successfully.")

    except sqlite3.IntegrityError:
        messagebox.showerror("Duplicate", "Roll number already exists.")
    except sqlite3.Error as error:
        notify_error(error)


def select_student(event=None):
    global selected_id
    selection = table.selection()
    if not selection:
        return

    row = table.item(selection[0], "values")
    selected_id = int(row[0])

    for var, value in zip(
        (name_var, roll_var, dept_var, email_var, phone_var), row[1:]
    ):
        var.set(value)

    form_title.config(text="Edit Student")
    save_btn.config(text="Save Changes", command=update_student)


def update_student():
    if selected_id is None:
        return

    data = form_data()
    if not validate(data):
        return

    try:
        with connect() as con:
            con.execute("""
                UPDATE students
                SET name=?, roll_no=?, department=?, email=?, phone=?
                WHERE id=?
            """, (*data, selected_id))

        clear_form()
        refresh()
        messagebox.showinfo("Success", "Student updated successfully.")

    except sqlite3.IntegrityError:
        messagebox.showerror("Duplicate", "Roll number already exists.")
    except sqlite3.Error as error:
        notify_error(error)


def delete_student():
    if selected_id is None:
        messagebox.showwarning("Select Student", "Select a record first.")
        return

    if not messagebox.askyesno("Confirm", "Delete this student?"):
        return

    try:
        with connect() as con:
            con.execute("DELETE FROM students WHERE id=?", (selected_id,))

        clear_form()
        refresh()

    except sqlite3.Error as error:
        notify_error(error)


# SEARCH AND STATISTICS
def refresh(event=None):
    try:
        keyword = f"%{search_var.get().strip()}%"
        department = filter_var.get()

        query = """
            SELECT id, name, roll_no, department, email, phone
            FROM students
            WHERE (name LIKE ? OR roll_no LIKE ?
                OR department LIKE ? OR email LIKE ? OR phone LIKE ?)
        """
        params = [keyword] * 5

        if department != "All":
            query += " AND department = ?"
            params.append(department)

        query += " ORDER BY id DESC"

        with connect() as con:
            records = con.execute(query, params).fetchall()
            total, departments = con.execute("""
                SELECT COUNT(*), COUNT(DISTINCT department)
                FROM students
            """).fetchone()

        table.delete(*table.get_children())

        for record in records:
            table.insert("", "end", values=record)

        total_value.config(text=str(total))
        dept_value.config(text=str(departments))
        shown_value.config(text=str(len(records)))
        count_label.config(text=f"{len(records)} records shown")

    except sqlite3.Error as error:
        notify_error(error)


def reset_search():
    search_var.set("")
    filter_var.set("All")
    refresh()


# CSV EXPORT
def export_csv():
    try:
        with connect() as con:
            rows = con.execute("""
                SELECT id, name, roll_no, department, email, phone
                FROM students ORDER BY id
            """).fetchall()

        if not rows:
            messagebox.showinfo("Empty", "No records to export.")
            return

        path = filedialog.asksaveasfilename(
            title="Export Students",
            defaultextension=".csv",
            initialfile="students.csv",
            filetypes=[("CSV files", "*.csv")]
        )
        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow([
                "ID", "Name", "Roll Number",
                "Department", "Email", "Phone"
            ])
            writer.writerows(rows)

        messagebox.showinfo("Exported", "CSV saved successfully.")

    except (OSError, sqlite3.Error) as error:
        notify_error(error)


# THEME
def apply_theme():
    c = theme
    root.config(bg=c["bg"])

    for frame in (main, topbar, content, stats, search_frame):
        frame.config(bg=c["bg"])

    sidebar.config(bg=c["sidebar"])
    for widget in sidebar.winfo_children():
        if isinstance(widget, tk.Label):
            widget.config(bg=c["sidebar"])

    for frame in (form, table_card):
        frame.config(bg=c["card"])

    for widget in root.winfo_children():
        recolor(widget, c)

    style.configure(
        "Treeview",
        background=c["card"], foreground=c["fg"],
        fieldbackground=c["card"], rowheight=32
    )
    style.configure(
        "Treeview.Heading",
        background="#334155" if theme is DARK else "#DBEAFE",
        foreground="white" if theme is DARK else "#1E3A8A",
        padding=7
    )
    style.map(
        "Treeview",
        background=[("selected", "#2563EB")],
        foreground=[("selected", "white")]
    )
    style.configure(
        "TCombobox",
        fieldbackground=c["input"], foreground=c["fg"]
    )
    refresh()


def recolor(widget, c):
    if isinstance(widget, tk.Button):
        return

    if isinstance(widget, tk.Frame):
        bg = c["sidebar"] if widget.master == sidebar else (
            c["card"] if widget in (form, table_card) else c["bg"]
        )
        try:
            widget.config(bg=bg)
        except tk.TclError:
            pass

    elif isinstance(widget, tk.Label):
        parent = widget.master
        if parent == sidebar:
            bg = c["sidebar"]
        elif parent in (form, table_card):
            bg = c["card"]
        elif parent in (main, topbar, content, stats, search_frame):
            bg = c["bg"]
        else:
            bg = c["card"]
        widget.config(bg=bg, fg=c["fg"])

    elif isinstance(widget, tk.LabelFrame):
        widget.config(bg=c["card"], fg=c["fg"])

    for child in widget.winfo_children():
        recolor(child, c)


def toggle_theme():
    global theme
    theme = DARK if theme is LIGHT else LIGHT
    theme_btn.config(text="Light Mode" if theme is DARK else "Dark Mode")
    apply_theme()


# STARTUP
setup_db()

root = tk.Tk()
root.title("Student Hub")
root.geometry("1200x740")
root.minsize(950, 620)

style = ttk.Style(root)
style.theme_use("clam")

name_var = tk.StringVar()
roll_var = tk.StringVar()
dept_var = tk.StringVar()
email_var = tk.StringVar()
phone_var = tk.StringVar()
search_var = tk.StringVar()
filter_var = tk.StringVar(value="All")


# SIDEBAR
sidebar = tk.Frame(root, bg=LIGHT["sidebar"], width=205)
sidebar.pack(side="left", fill="y")
sidebar.pack_propagate(False)

tk.Label(
    sidebar, text="STUDENT HUB",
    font=("Segoe UI", 17, "bold"),
    bg=LIGHT["sidebar"], fg="white"
).pack(padx=15, pady=(28, 5), anchor="w")

tk.Label(
    sidebar, text="MANAGEMENT SYSTEM",
    font=("Segoe UI", 9),
    bg=LIGHT["sidebar"], fg="#93C5FD"
).pack(padx=15, pady=(0, 30), anchor="w")

button(sidebar, "Dashboard", reset_search, LIGHT["sidebar"]).pack(
    fill="x", padx=10, pady=5
)
button(sidebar, "Student Records", lambda: name_entry.focus_set(),
       LIGHT["sidebar"]).pack(fill="x", padx=10, pady=5)
button(sidebar, "Export CSV", export_csv, LIGHT["sidebar"]).pack(
    fill="x", padx=10, pady=5
)

tk.Label(
    sidebar, text="Python | Tkinter | SQLite",
    bg=LIGHT["sidebar"], fg="#94A3B8",
    font=("Segoe UI", 9)
).pack(side="bottom", padx=12, pady=20)


# MAIN AREA
main = tk.Frame(root, bg=LIGHT["bg"])
main.pack(side="left", fill="both", expand=True)

topbar = tk.Frame(main, bg=LIGHT["bg"])
topbar.pack(fill="x", padx=24, pady=18)

tk.Label(
    topbar, text="Student Dashboard",
    font=("Segoe UI", 21, "bold"),
    bg=LIGHT["bg"], fg=LIGHT["fg"]
).pack(side="left")

theme_btn = button(topbar, "Dark Mode", toggle_theme, "#475569")
theme_btn.pack(side="right")

tk.Label(
    topbar, text=date.today().strftime("%d %b %Y"),
    bg=LIGHT["bg"], fg=LIGHT["muted"]
).pack(side="right", padx=15)

content = tk.Frame(main, bg=LIGHT["bg"])
content.pack(fill="both", expand=True, padx=24, pady=(0, 18))


# STATISTICS
stats = tk.Frame(content, bg=LIGHT["bg"])
stats.pack(fill="x", pady=(0, 14))


def stat_card(title, color):
    card = tk.Frame(stats, bg=LIGHT["card"], padx=16, pady=12)
    card.pack(side="left", fill="both", expand=True, padx=(0, 10))
    tk.Label(card, text=title, bg=LIGHT["card"],
             fg=LIGHT["muted"]).pack(anchor="w")
    value = tk.Label(card, text="0", bg=LIGHT["card"],
                     fg=color, font=("Segoe UI", 23, "bold"))
    value.pack(anchor="w")
    return value


total_value = stat_card("TOTAL STUDENTS", "#2563EB")
dept_value = stat_card("DEPARTMENTS", "#059669")
shown_value = stat_card("FILTERED RESULTS", "#D97706")


# FORM
form = tk.LabelFrame(
    content, text=" Student Information ",
    bg=LIGHT["card"], fg=LIGHT["fg"],
    font=("Segoe UI", 11, "bold"), padx=12, pady=10
)
form.pack(fill="x", pady=(0, 12))

form_title = tk.Label(
    form, text="Add New Student",
    bg=LIGHT["card"], fg=LIGHT["fg"],
    font=("Segoe UI", 12, "bold")
)
form_title.grid(row=0, column=0, columnspan=3, sticky="w", pady=5)

fields = [
    ("Name", name_var),
    ("Roll Number", roll_var),
    ("Department", dept_var),
    ("Email", email_var),
    ("Phone", phone_var)
]
name_entry = None

for i, (label, var) in enumerate(fields):
    r, col = 1 + (i // 3) * 2, i % 3

    tk.Label(form, text=label, bg=LIGHT["card"],
             fg=LIGHT["fg"]).grid(row=r, column=col,
                                  sticky="w", padx=5, pady=(4, 2))

    if label == "Department":
        field = ttk.Combobox(
            form, textvariable=var, values=DEPARTMENTS, width=26
        )
    else:
        field = ttk.Entry(form, textvariable=var, width=29)

    field.grid(row=r + 1, column=col, sticky="ew", padx=5, pady=3)

    if label == "Name":
        name_entry = field

for col in range(3):
    form.columnconfigure(col, weight=1)

save_btn = button(form, "Add Student", add_student)
save_btn.grid(row=5, column=0, sticky="w", padx=5, pady=8)

button(form, "Clear Form", clear_form, "#64748B").grid(
    row=5, column=1, sticky="w", padx=5, pady=8
)
button(form, "Delete Selected", delete_student, "#DC2626").grid(
    row=5, column=2, sticky="w", padx=5, pady=8
)


# SEARCH
search_frame = tk.Frame(content, bg=LIGHT["bg"])
search_frame.pack(fill="x", pady=(0, 10))

tk.Label(search_frame, text="Search:", bg=LIGHT["bg"],
         fg=LIGHT["fg"]).pack(side="left", padx=(0, 6))

search_entry = ttk.Entry(search_frame, textvariable=search_var, width=24)
search_entry.pack(side="left", ipady=3)

filter_box = ttk.Combobox(
    search_frame, textvariable=filter_var,
    values=["All"] + DEPARTMENTS, state="readonly", width=23
)
filter_box.pack(side="left", padx=8)

button(search_frame, "Reset", reset_search, "#64748B").pack(side="left")

search_var.trace_add("write", refresh)
filter_box.bind("<<ComboboxSelected>>", refresh)


# TABLE
table_card = tk.Frame(content, bg=LIGHT["card"])
table_card.pack(fill="both", expand=True)

tk.Label(
    table_card, text="Student Directory",
    font=("Segoe UI", 12, "bold"),
    bg=LIGHT["card"], fg=LIGHT["fg"]
).pack(anchor="w", padx=12, pady=10)

columns = ("ID", "Name", "Roll No", "Department", "Email", "Phone")
table_frame = tk.Frame(table_card, bg=LIGHT["card"])
table_frame.pack(fill="both", expand=True, padx=10)

table = ttk.Treeview(
    table_frame, columns=columns, show="headings",
    selectmode="browse"
)

for col, width in zip(columns, (45, 145, 100, 160, 190, 115)):
    table.heading(col, text=col)
    table.column(col, width=width, minwidth=60)

yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=table.xview)

table.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
table.grid(row=0, column=0, sticky="nsew")
yscroll.grid(row=0, column=1, sticky="ns")
xscroll.grid(row=1, column=0, sticky="ew")

table_frame.rowconfigure(0, weight=1)
table_frame.columnconfigure(0, weight=1)

table.bind("<<TreeviewSelect>>", select_student)

count_label = tk.Label(
    table_card, text="0 records shown",
    bg=LIGHT["card"], fg=LIGHT["muted"]
)
count_label.pack(anchor="w", padx=12, pady=8)

root.bind("<Control-f>", lambda e: search_entry.focus_set())
root.bind("<Control-n>", lambda e: clear_form())
root.bind("<Escape>", lambda e: clear_form())

apply_theme()
root.mainloop()
