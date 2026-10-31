import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import cv2
import face_recognition
import os
import shutil
import sys
from datetime import datetime
from PIL import Image, ImageTk
from liveness import LivenessChallenge


# ============================================================
# SMART ATTENDANCE SYSTEM
# PROFESSIONAL ALL-IN-ONE GUI
# ============================================================


# ============================================================
# SETTINGS
# ============================================================

APP_TITLE = "SMART ATTENDANCE SYSTEM"

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800

SOURCE_FOLDER = os.path.dirname(os.path.abspath(__file__))

if getattr(sys, "frozen", False):
    # A packaged macOS app cannot write inside its own application bundle.
    # Keep user data in the standard per-user Application Support location.
    APP_DATA_FOLDER = os.path.join(
        os.path.expanduser("~/Library/Application Support"),
        "Smart Attendance",
    )
    os.makedirs(APP_DATA_FOLDER, exist_ok=True)

    for folder_name in ("database", "known_faces"):
        source = os.path.join(sys._MEIPASS, folder_name)
        destination = os.path.join(APP_DATA_FOLDER, folder_name)
        if os.path.exists(source) and not os.path.exists(destination):
            shutil.copytree(source, destination)

    DATABASE_FOLDER = os.path.join(APP_DATA_FOLDER, "database")
    KNOWN_FACES_FOLDER = os.path.join(APP_DATA_FOLDER, "known_faces")
else:
    DATABASE_FOLDER = os.path.join(SOURCE_FOLDER, "database")
    KNOWN_FACES_FOLDER = os.path.join(SOURCE_FOLDER, "known_faces")

DATABASE_FILE = os.path.join(DATABASE_FOLDER, "attendance.db")

FACE_TOLERANCE = 0.50

os.makedirs(
    DATABASE_FOLDER,
    exist_ok=True
)

os.makedirs(
    KNOWN_FACES_FOLDER,
    exist_ok=True
)


# ============================================================
# COLORS
# ============================================================

BG = "#0b1220"
SIDEBAR = "#111827"
SIDEBAR_ACTIVE = "#1f2937"

CARD = "#172033"
CARD_2 = "#1e293b"

WHITE = "#f8fafc"
TEXT = "#dbe4f0"
MUTED = "#94a3b8"

BLUE = "#2563eb"
BLUE_HOVER = "#1d4ed8"

GREEN = "#22c55e"
RED = "#ef4444"
PURPLE = "#8b5cf6"
ORANGE = "#f59e0b"


# ============================================================
# DATABASE
# ============================================================

def get_connection():

    return sqlite3.connect(
        DATABASE_FILE
    )


def create_tables():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            department TEXT,
            email TEXT,
            face_image TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT NOT NULL,
            confidence REAL
        )
    """)

    connection.commit()
    connection.close()


create_tables()


# ============================================================
# DATABASE FUNCTIONS
# ============================================================

def get_student(student_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            student_id,
            name,
            department,
            email,
            face_image
        FROM students
        WHERE student_id = ?
    """, (student_id,))

    result = cursor.fetchone()

    connection.close()

    return result


def get_all_students():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            student_id,
            name,
            department,
            email,
            face_image
        FROM students
        ORDER BY name
    """)

    results = cursor.fetchall()

    connection.close()

    return results


def add_student(
    student_id,
    name,
    department,
    email,
    face_image
):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            INSERT INTO students
            (
                student_id,
                name,
                department,
                email,
                face_image
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            student_id,
            name,
            department,
            email,
            face_image
        ))

        connection.commit()

        connection.close()

        return True

    except sqlite3.IntegrityError:

        connection.close()

        return False


def delete_student(student_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM attendance
        WHERE student_id = ?
    """, (student_id,))

    cursor.execute("""
        DELETE FROM students
        WHERE student_id = ?
    """, (student_id,))

    deleted = cursor.rowcount

    connection.commit()
    connection.close()

    return deleted > 0


def has_attendance_today(student_id):

    connection = get_connection()
    cursor = connection.cursor()

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    cursor.execute("""
        SELECT id
        FROM attendance
        WHERE student_id = ?
        AND date = ?
    """, (
        student_id,
        today
    ))

    result = cursor.fetchone()

    connection.close()

    return result is not None


def mark_attendance(
    student_id,
    confidence=0.0
):

    if has_attendance_today(student_id):

        return False

    connection = get_connection()
    cursor = connection.cursor()

    now = datetime.now()

    date = now.strftime(
        "%Y-%m-%d"
    )

    time = now.strftime(
        "%H:%M:%S"
    )

    cursor.execute("""
        INSERT INTO attendance
        (
            student_id,
            date,
            time,
            status,
            confidence
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        student_id,
        date,
        time,
        "Present",
        confidence
    ))

    connection.commit()
    connection.close()

    return True


def get_attendance():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            attendance.student_id,
            students.name,
            students.department,
            attendance.date,
            attendance.time,
            attendance.status,
            attendance.confidence
        FROM attendance
        LEFT JOIN students
        ON attendance.student_id =
           students.student_id
        ORDER BY
            attendance.date DESC,
            attendance.time DESC
    """)

    records = cursor.fetchall()

    connection.close()

    return records


# ============================================================
# MAIN WINDOW
# ============================================================

window = tk.Tk()

window.title(
    APP_TITLE
)

window.geometry(
    f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}"
)

window.minsize(
    1100,
    700
)

window.configure(
    bg=BG
)


# ============================================================
# CAMERA VARIABLES
# ============================================================

camera = None
camera_running = False
camera_mode = None

camera_after_id = None
liveness_challenge = None
liveness_student_id = None


# ============================================================
# FACE DATA
# ============================================================

known_face_encodings = []
known_face_ids = []


# ============================================================
# LOAD REGISTERED FACES
# ============================================================

def load_known_faces():

    global known_face_encodings
    global known_face_ids

    known_face_encodings = []
    known_face_ids = []

    if not os.path.exists(
        KNOWN_FACES_FOLDER
    ):
        return

    for filename in os.listdir(
        KNOWN_FACES_FOLDER
    ):

        if not filename.lower().endswith(
            (
                ".jpg",
                ".jpeg",
                ".png"
            )
        ):
            continue

        path = os.path.join(
            KNOWN_FACES_FOLDER,
            filename
        )

        try:

            image = face_recognition.load_image_file(
                path
            )

            encodings = face_recognition.face_encodings(
                image
            )

            if not encodings:

                print(
                    f"No face found: {filename}"
                )

                continue

            student_id = os.path.splitext(
                filename
            )[0]

            known_face_encodings.append(
                encodings[0]
            )

            known_face_ids.append(
                student_id
            )

            print(
                f"Loaded face: {student_id}"
            )

        except Exception as error:

            print(
                f"Error loading {filename}: {error}"
            )


load_known_faces()


# ============================================================
# STOP CAMERA
# ============================================================

def stop_camera():

    global camera
    global camera_running
    global camera_after_id
    global liveness_challenge
    global liveness_student_id

    camera_running = False

    if camera_after_id is not None:

        try:
            window.after_cancel(
                camera_after_id
            )
        except:
            pass

        camera_after_id = None

    if camera is not None:

        try:
            camera.release()
        except:
            pass

        camera = None

    if liveness_challenge is not None:
        try:
            liveness_challenge.close()
        except Exception:
            pass
        liveness_challenge = None
        liveness_student_id = None


# ============================================================
# SIDEBAR
# ============================================================

sidebar = tk.Frame(
    window,
    bg=SIDEBAR,
    width=230
)

sidebar.pack(
    side="left",
    fill="y"
)

sidebar.pack_propagate(
    False
)


# ============================================================
# SIDEBAR HEADER
# ============================================================

logo_frame = tk.Frame(
    sidebar,
    bg=SIDEBAR
)

logo_frame.pack(
    fill="x",
    pady=(25, 15)
)


logo = tk.Label(
    logo_frame,
    text="SMART\nATTENDANCE",
    font=("Arial", 20, "bold"),
    bg=SIDEBAR,
    fg=WHITE
)

logo.pack()


subtitle = tk.Label(
    logo_frame,
    text="FACE RECOGNITION SYSTEM",
    font=("Arial", 8),
    bg=SIDEBAR,
    fg=MUTED
)

subtitle.pack(
    pady=(5, 0)
)


# ============================================================
# SIDEBAR BUTTON
# ============================================================

def add_sidebar_button(
    text,
    command
):

    button_frame = tk.Frame(
        sidebar,
        bg=SIDEBAR,
        height=50
    )

    button_frame.pack(
        fill="x",
        padx=12,
        pady=3
    )

    button_frame.pack_propagate(
        False
    )

    label = tk.Label(
        button_frame,
        text=text,
        font=("Arial", 11, "bold"),
        bg=SIDEBAR,
        fg=WHITE,
        anchor="w",
        padx=18,
        cursor="hand2"
    )

    label.pack(
        fill="both",
        expand=True
    )

    def enter(event):

        button_frame.config(
            bg=SIDEBAR_ACTIVE
        )

        label.config(
            bg=SIDEBAR_ACTIVE
        )

    def leave(event):

        button_frame.config(
            bg=SIDEBAR
        )

        label.config(
            bg=SIDEBAR
        )

    def click(event):

        command()

    for widget in (
        button_frame,
        label
    ):

        widget.bind(
            "<Enter>",
            enter
        )

        widget.bind(
            "<Leave>",
            leave
        )

        widget.bind(
            "<Button-1>",
            click
        )


# ============================================================
# CONTENT AREA
# ============================================================

content = tk.Frame(
    window,
    bg=BG
)

content.pack(
    side="right",
    fill="both",
    expand=True
)


# ============================================================
# PAGE CONTAINER
# ============================================================

page_container = tk.Frame(
    content,
    bg=BG
)

page_container.pack(
    fill="both",
    expand=True,
    padx=25,
    pady=20
)


# ============================================================
# PAGE HELPERS
# ============================================================

current_page = None


def clear_page():

    global current_page

    stop_camera()

    for widget in page_container.winfo_children():

        widget.destroy()

    current_page = None


def page_title(
    title,
    subtitle_text=""
):

    frame = tk.Frame(
        page_container,
        bg=BG
    )

    frame.pack(
        fill="x",
        pady=(0, 20)
    )

    tk.Label(
        frame,
        text=title,
        font=("Arial", 27, "bold"),
        bg=BG,
        fg=WHITE
    ).pack(
        anchor="w"
    )

    if subtitle_text:

        tk.Label(
            frame,
            text=subtitle_text,
            font=("Arial", 11),
            bg=BG,
            fg=MUTED
        ).pack(
            anchor="w",
            pady=(5, 0)
        )


# ============================================================
# DASHBOARD
# ============================================================

def dashboard_page():

    clear_page()

    page_title(
        "Dashboard",
        "Welcome to Smart Attendance System"
    )

    # --------------------------------------------------------
    # STATISTICS
    # --------------------------------------------------------

    stats_frame = tk.Frame(
        page_container,
        bg=BG
    )

    stats_frame.pack(
        fill="x"
    )

    students = get_all_students()

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM attendance
        WHERE date = ?
    """, (today,))

    today_present = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM attendance
    """)

    total_attendance = cursor.fetchone()[0]

    connection.close()

    create_stat_card(
        stats_frame,
        "REGISTERED STUDENTS",
        str(len(students)),
        BLUE,
        0
    )

    create_stat_card(
        stats_frame,
        "TODAY PRESENT",
        str(today_present),
        GREEN,
        1
    )

    create_stat_card(
        stats_frame,
        "TOTAL ATTENDANCE",
        str(total_attendance),
        PURPLE,
        2
    )

    # --------------------------------------------------------
    # QUICK ACTIONS
    # --------------------------------------------------------

    tk.Label(
        page_container,
        text="Quick Actions",
        font=("Arial", 17, "bold"),
        bg=BG,
        fg=WHITE
    ).pack(
        anchor="w",
        pady=(35, 15)
    )

    actions = tk.Frame(
        page_container,
        bg=BG
    )

    actions.pack(
        fill="x"
    )

    create_action_button(
        actions,
        "MARK ATTENDANCE",
        attendance_page,
        0
    )

    create_action_button(
        actions,
        "REGISTER STUDENT",
        register_page,
        1
    )

    create_action_button(
        actions,
        "VIEW ATTENDANCE",
        attendance_records_page,
        2
    )


def create_stat_card(
    parent,
    title,
    value,
    accent,
    column
):

    card = tk.Frame(
        parent,
        bg=CARD,
        height=145
    )

    card.grid(
        row=0,
        column=column,
        padx=8,
        sticky="nsew"
    )

    parent.grid_columnconfigure(
        column,
        weight=1
    )

    card.pack_propagate(
        False
    )

    tk.Frame(
        card,
        bg=accent,
        width=6
    ).pack(
        side="left",
        fill="y"
    )

    tk.Label(
        card,
        text=title,
        font=("Arial", 10, "bold"),
        bg=CARD,
        fg=MUTED
    ).pack(
        anchor="w",
        padx=20,
        pady=(25, 5)
    )

    tk.Label(
        card,
        text=value,
        font=("Arial", 32, "bold"),
        bg=CARD,
        fg=WHITE
    ).pack(
        anchor="w",
        padx=20
    )


def create_action_button(
    parent,
    text,
    command,
    column
):

    button = tk.Label(
        parent,
        text=text,
        font=("Arial", 11, "bold"),
        bg=CARD_2,
        fg=WHITE,
        cursor="hand2",
        padx=25,
        pady=20
    )

    button.grid(
        row=0,
        column=column,
        padx=8,
        sticky="ew"
    )

    parent.grid_columnconfigure(
        column,
        weight=1
    )

    def enter(event):

        button.config(
            bg=BLUE
        )

    def leave(event):

        button.config(
            bg=CARD_2
        )

    def click(event):

        command()

    button.bind(
        "<Enter>",
        enter
    )

    button.bind(
        "<Leave>",
        leave
    )

    button.bind(
        "<Button-1>",
        click
    )


# ============================================================
# ATTENDANCE PAGE
# ============================================================

def attendance_page():

    clear_page()

    page_title(
        "Mark Attendance",
        "Face recognition attendance"
    )

    main = tk.Frame(
        page_container,
        bg=BG
    )

    main.pack(
        fill="both",
        expand=True
    )

    # --------------------------------------------------------
    # CAMERA CONTAINER
    # --------------------------------------------------------

    camera_container = tk.Frame(
        main,
        bg="#000000",
        width=760,
        height=500
    )

    camera_container.pack(
        side="left",
        fill="both",
        expand=True,
        padx=(0, 15)
    )

    camera_container.pack_propagate(
        False
    )

    camera_label = tk.Label(
        camera_container,
        text="Camera stopped\n\nClick START CAMERA",
        font=("Arial", 18),
        bg="#000000",
        fg=WHITE
    )

    camera_label.pack(
        fill="both",
        expand=True
    )

    # --------------------------------------------------------
    # INFO PANEL
    # --------------------------------------------------------

    info = tk.Frame(
        main,
        bg=CARD,
        width=300
    )

    info.pack(
        side="right",
        fill="y"
    )

    info.pack_propagate(
        False
    )

    tk.Label(
        info,
        text="STUDENT INFORMATION",
        font=("Arial", 15, "bold"),
        bg=CARD,
        fg=WHITE
    ).pack(
        pady=25
    )

    name_label = create_info_label(
        info,
        "Name: ---"
    )

    id_label = create_info_label(
        info,
        "Student ID: ---"
    )

    department_label = create_info_label(
        info,
        "Department: ---"
    )

    status_label = create_info_label(
        info,
        "Attendance: ---"
    )

    face_label = create_info_label(
        info,
        "Face: Not detected"
    )

    system_label = tk.Label(
        info,
        text="System ready",
        font=("Arial", 10),
        bg=CARD,
        fg=MUTED,
        wraplength=250
    )

    system_label.pack(
        padx=20,
        pady=20
    )

    # --------------------------------------------------------
    # BUTTONS
    # --------------------------------------------------------

    buttons = tk.Frame(
        page_container,
        bg=BG
    )

    buttons.pack(
        pady=15
    )

    create_bottom_button(
        buttons,
        "START CAMERA",
        lambda: start_attendance_camera(
            camera_label,
            name_label,
            id_label,
            department_label,
            status_label,
            face_label,
            system_label
        ),
        BLUE
    )

    create_bottom_button(
        buttons,
        "STOP CAMERA",
        stop_camera,
        RED
    )


def create_info_label(
    parent,
    text
):

    label = tk.Label(
        parent,
        text=text,
        font=("Arial", 11),
        bg=CARD,
        fg=TEXT,
        anchor="w",
        wraplength=250
    )

    label.pack(
        fill="x",
        padx=20,
        pady=12
    )

    return label


def create_bottom_button(
    parent,
    text,
    command,
    bg_color
):

    button = tk.Label(
        parent,
        text=text,
        font=("Arial", 11, "bold"),
        bg=bg_color,
        fg=WHITE,
        cursor="hand2",
        padx=25,
        pady=12
    )

    button.pack(
        side="left",
        padx=8
    )

    button.bind(
        "<Button-1>",
        lambda event: command()
    )


# ============================================================
# START ATTENDANCE CAMERA
# ============================================================

def start_attendance_camera(
    camera_label,
    name_label,
    id_label,
    department_label,
    status_label,
    face_label,
    system_label
):

    global camera
    global camera_running
    global camera_mode

    if camera_running:

        return

    camera = cv2.VideoCapture(
        0,
        cv2.CAP_AVFOUNDATION
    )

    if not camera.isOpened():

        camera.release()

        camera = cv2.VideoCapture(0)

    if not camera.isOpened():

        messagebox.showerror(
            "Camera Error",
            "Could not open camera."
        )

        camera = None

        return

    camera.set(
        cv2.CAP_PROP_FRAME_WIDTH,
        640
    )

    camera.set(
        cv2.CAP_PROP_FRAME_HEIGHT,
        480
    )

    camera_running = True
    camera_mode = "attendance"

    system_label.config(
        text="Camera running. Looking for a registered face..."
    )

    global liveness_challenge
    global liveness_student_id
    liveness_challenge = LivenessChallenge()
    liveness_student_id = None

    update_attendance_camera(
        camera_label,
        name_label,
        id_label,
        department_label,
        status_label,
        face_label,
        system_label
    )


# ============================================================
# UPDATE ATTENDANCE CAMERA
# ============================================================

def update_attendance_camera(
    camera_label,
    name_label,
    id_label,
    department_label,
    status_label,
    face_label,
    system_label
):

    global camera_after_id
    global liveness_challenge
    global liveness_student_id

    if not camera_running:

        return

    if camera is None:

        return

    success, frame = camera.read()

    if not success:

        camera_after_id = window.after(
            100,
            lambda: update_attendance_camera(
                camera_label,
                name_label,
                id_label,
                department_label,
                status_label,
                face_label,
                system_label
            )
        )

        return

    small = cv2.resize(
        frame,
        (0, 0),
        fx=0.25,
        fy=0.25
    )

    rgb = cv2.cvtColor(
        small,
        cv2.COLOR_BGR2RGB
    )

    locations = face_recognition.face_locations(
        rgb
    )

    encodings = face_recognition.face_encodings(
        rgb,
        locations
    )

    recognized = False
    recognized_student_id = None
    recognized_name = "Unknown"
    recognized_department = "N/A"
    recognized_confidence = 0.0
    primary_face_box = None
    primary_face_location = None

    for encoding, location in zip(
        encodings,
        locations
    ):

        top, right, bottom, left = location

        top *= 4
        right *= 4
        bottom *= 4
        left *= 4

        name = "Unknown"
        student_id = None
        confidence = 0.0

        if known_face_encodings:

            distances = face_recognition.face_distance(
                known_face_encodings,
                encoding
            )

            best_index = distances.argmin()

            distance = distances[
                best_index
            ]

            confidence = max(
                0.0,
                min(
                    1.0,
                    1.0 - distance
                )
            )

            matches = face_recognition.compare_faces(
                known_face_encodings,
                encoding,
                tolerance=FACE_TOLERANCE
            )

            if matches[best_index]:

                student_id = known_face_ids[
                    best_index
                ]

                student = get_student(
                    student_id
                )

                if student:

                    name = student[1]

                    department = (
                        student[2]
                        if student[2]
                        else "N/A"
                    )

                else:

                    department = "N/A"

                recognized = True
                recognized_student_id = student_id
                recognized_name = name
                recognized_department = department
                recognized_confidence = confidence
                primary_face_box = (left, top, right, bottom)
                primary_face_location = (top, right, bottom, left)

        if student_id:

            color = (
                0,
                255,
                0
            )

            face_label.config(
                text="Face: Recognized"
            )

            name_label.config(
                text=f"Name: {name}"
            )

            id_label.config(
                text=f"Student ID: {student_id}"
            )

            department_label.config(
                text=f"Department: {department}"
            )

        else:

            color = (
                255,
                0,
                0
            )

            face_label.config(
                text="Face: Unknown"
            )

        cv2.rectangle(
            frame,
            (left, top),
            (right, bottom),
            color,
            2
        )

        cv2.rectangle(
            frame,
            (
                left,
                bottom - 35
            ),
            (
                right,
                bottom
            ),
            color,
            -1
        )

        cv2.putText(
            frame,
            name,
            (
                left + 5,
                bottom - 9
            ),
            cv2.FONT_HERSHEY_DUPLEX,
            0.65,
            (0, 0, 0),
            1
        )

        cv2.putText(
            frame,
            f"{confidence:.2f}",
            (
                left,
                max(20, top - 10)
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2
        )

    if not locations:

        face_label.config(
            text="Face: Not detected"
        )

        system_label.config(
            text="Searching for face..."
        )

    # Only a recognized person can complete the active liveness challenge.
    if recognized and len(locations) == 1 and liveness_challenge is not None:
        # Do not let a partial challenge be transferred to a different person.
        if liveness_student_id != recognized_student_id:
            liveness_challenge.reset()
            liveness_student_id = recognized_student_id
        result = liveness_challenge.process(frame, primary_face_location)
        system_label.config(text=result["status"])
        status_label.config(
            text=f"Attendance: {result['status']}",
            fg=ORANGE if not result["passed"] else GREEN,
        )

        if result["passed"]:
            marked = mark_attendance(recognized_student_id, recognized_confidence)
            if marked:
                now = datetime.now().strftime("%H:%M:%S")
                status_label.config(text=f"Attendance: PRESENT\nTime: {now}", fg=GREEN)
                system_label.config(text="Attendance marked after liveness verification.")
            else:
                status_label.config(text="Attendance: ALREADY MARKED", fg=ORANGE)
                system_label.config(text="This student is already marked present today.")
            # A new challenge is required for the next recognised face.
            liveness_challenge.reset()
    elif liveness_challenge is not None:
        liveness_challenge.reset()
        liveness_student_id = None

    display_camera_frame(
        camera_label,
        frame
    )

    camera_after_id = window.after(
        80,
        lambda: update_attendance_camera(
            camera_label,
            name_label,
            id_label,
            department_label,
            status_label,
            face_label,
            system_label
        )
    )


# ============================================================
# DISPLAY CAMERA FRAME
# ============================================================

def display_camera_frame(
    label,
    frame
):

    rgb = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    image = Image.fromarray(
        rgb
    )

    # IMPORTANT:
    # Fixed display size prevents camera growth.

    width = 720
    height = 500

    image.thumbnail(
        (
            width,
            height
        ),
        Image.Resampling.LANCZOS
    )

    background = Image.new(
        "RGB",
        (
            width,
            height
        ),
        "black"
    )

    x = (
        width - image.width
    ) // 2

    y = (
        height - image.height
    ) // 2

    background.paste(
        image,
        (x, y)
    )

    photo = ImageTk.PhotoImage(
        background
    )

    label.config(
        image=photo,
        text=""
    )

    label.image = photo


# ============================================================
# REGISTER STUDENT PAGE
# ============================================================

def register_page():

    clear_page()

    page_title(
        "Register Student",
        "Add a new student and capture their face"
    )

    main = tk.Frame(
        page_container,
        bg=BG
    )

    main.pack(
        fill="both",
        expand=True
    )

    # --------------------------------------------------------
    # LEFT FORM
    # --------------------------------------------------------

    form = tk.Frame(
        main,
        bg=CARD,
        width=400
    )

    form.pack(
        side="left",
        fill="y",
        padx=(0, 15)
    )

    form.pack_propagate(
        False
    )

    tk.Label(
        form,
        text="STUDENT DETAILS",
        font=("Arial", 16, "bold"),
        bg=CARD,
        fg=WHITE
    ).pack(
        pady=25
    )

    student_id_entry = create_entry(
        form,
        "Student ID"
    )

    name_entry = create_entry(
        form,
        "Student Name"
    )

    department_entry = create_entry(
        form,
        "Department"
    )

    email_entry = create_entry(
        form,
        "Email"
    )

    # --------------------------------------------------------
    # RIGHT CAMERA
    # --------------------------------------------------------

    camera_box = tk.Frame(
        main,
        bg=CARD
    )

    camera_box.pack(
        side="right",
        fill="both",
        expand=True
    )

    tk.Label(
        camera_box,
        text="FACE CAPTURE",
        font=("Arial", 16, "bold"),
        bg=CARD,
        fg=WHITE
    ).pack(
        pady=15
    )

    # FIXED CAMERA FRAME
    camera_display = tk.Frame(
        camera_box,
        bg="#000000",
        width=640,
        height=430
    )

    camera_display.pack(
        padx=20
    )

    camera_display.pack_propagate(
        False
    )

    registration_camera_label = tk.Label(
        camera_display,
        text="Click START CAMERA",
        font=("Arial", 16),
        bg="#000000",
        fg=WHITE
    )

    registration_camera_label.pack(
        fill="both",
        expand=True
    )

    instruction = tk.Label(
        camera_box,
        text="Look at the camera and press CAPTURE FACE.",
        font=("Arial", 10),
        bg=CARD,
        fg=MUTED
    )

    instruction.pack(
        pady=8
    )

    buttons = tk.Frame(
        camera_box,
        bg=CARD
    )

    buttons.pack(
        pady=10
    )

    create_small_button(
        buttons,
        "START CAMERA",
        lambda: start_registration_camera(
            registration_camera_label,
            student_id_entry,
            name_entry
        ),
        BLUE
    )

    create_small_button(
        buttons,
        "CAPTURE FACE",
        lambda: capture_registration_face(
            student_id_entry,
            name_entry,
            department_entry,
            email_entry,
            registration_camera_label
        ),
        GREEN
    )

    create_small_button(
        buttons,
        "STOP CAMERA",
        stop_camera,
        RED
    )


def create_entry(
    parent,
    placeholder
):

    label = tk.Label(
        parent,
        text=placeholder,
        font=("Arial", 10, "bold"),
        bg=CARD,
        fg=MUTED,
        anchor="w"
    )

    label.pack(
        fill="x",
        padx=25,
        pady=(10, 3)
    )

    entry = tk.Entry(
        parent,
        font=("Arial", 12),
        bg="#0f172a",
        fg=WHITE,
        insertbackground=WHITE,
        relief="flat"
    )

    entry.pack(
        fill="x",
        padx=25,
        ipady=10
    )

    return entry


def create_small_button(
    parent,
    text,
    command,
    color
):

    button = tk.Label(
        parent,
        text=text,
        font=("Arial", 9, "bold"),
        bg=color,
        fg=WHITE,
        cursor="hand2",
        padx=14,
        pady=10
    )

    button.pack(
        side="left",
        padx=5
    )

    button.bind(
        "<Button-1>",
        lambda event: command()
    )


# ============================================================
# START REGISTRATION CAMERA
# ============================================================

def start_registration_camera(
    camera_label,
    student_id_entry,
    name_entry
):

    global camera
    global camera_running
    global camera_mode

    if not student_id_entry.get().strip():

        messagebox.showwarning(
            "Missing Student ID",
            "Enter Student ID first."
        )

        return

    if not name_entry.get().strip():

        messagebox.showwarning(
            "Missing Name",
            "Enter Student Name first."
        )

        return

    if camera_running:

        return

    camera = cv2.VideoCapture(
        0,
        cv2.CAP_AVFOUNDATION
    )

    if not camera.isOpened():

        camera.release()

        camera = cv2.VideoCapture(0)

    if not camera.isOpened():

        messagebox.showerror(
            "Camera Error",
            "Could not open camera."
        )

        camera = None

        return

    # IMPORTANT:
    # Keep camera resolution fixed.

    camera.set(
        cv2.CAP_PROP_FRAME_WIDTH,
        640
    )

    camera.set(
        cv2.CAP_PROP_FRAME_HEIGHT,
        480
    )

    camera_running = True
    camera_mode = "registration"

    update_registration_camera(
        camera_label
    )


# ============================================================
# UPDATE REGISTRATION CAMERA
# ============================================================

def update_registration_camera(
    camera_label
):

    global camera_after_id

    if not camera_running:

        return

    if camera is None:

        return

    success, frame = camera.read()

    if not success:

        camera_after_id = window.after(
            100,
            lambda: update_registration_camera(
                camera_label
            )
        )

        return

    small = cv2.resize(
        frame,
        (0, 0),
        fx=0.50,
        fy=0.50
    )

    gray = cv2.cvtColor(
        small,
        cv2.COLOR_BGR2GRAY
    )

    faces = cv2.CascadeClassifier(
        cv2.data.haarcascades
        + "haarcascade_frontalface_default.xml"
    ).detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80)
    )

    for (
        x,
        y,
        w,
        h
    ) in faces:

        x *= 2
        y *= 2
        w *= 2
        h *= 2

        cv2.rectangle(
            frame,
            (x, y),
            (
                x + w,
                y + h
            ),
            (
                0,
                255,
                0
            ),
            2
        )

        cv2.putText(
            frame,
            "Face detected",
            (
                x,
                max(
                    25,
                    y - 10
                )
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (
                0,
                255,
                0
            ),
            2
        )

    display_camera_frame(
        camera_label,
        frame
    )

    camera_after_id = window.after(
        80,
        lambda: update_registration_camera(
            camera_label
        )
    )


# ============================================================
# CAPTURE REGISTRATION FACE
# ============================================================

def capture_registration_face(
    student_id_entry,
    name_entry,
    department_entry,
    email_entry,
    camera_label
):

    global camera

    student_id = student_id_entry.get().strip()
    name = name_entry.get().strip()
    department = department_entry.get().strip()
    email = email_entry.get().strip()

    if not student_id:

        messagebox.showwarning(
            "Missing Student ID",
            "Enter Student ID."
        )

        return

    if not name:

        messagebox.showwarning(
            "Missing Name",
            "Enter Student Name."
        )

        return

    if camera is None or not camera_running:

        messagebox.showwarning(
            "Camera Not Running",
            "Click START CAMERA first."
        )

        return

    success, frame = camera.read()

    if not success:

        messagebox.showerror(
            "Camera Error",
            "Could not capture camera frame."
        )

        return

    rgb = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    locations = face_recognition.face_locations(
        rgb
    )

    if len(locations) == 0:

        messagebox.showwarning(
            "No Face",
            "No face detected. Look directly at the camera."
        )

        return

    if len(locations) > 1:

        messagebox.showwarning(
            "Multiple Faces",
            "Only one person should be visible."
        )

        return

    top, right, bottom, left = locations[0]

    face_image = frame[
        top:bottom,
        left:right
    ]

    if face_image.size == 0:

        messagebox.showerror(
            "Capture Error",
            "Could not crop face."
        )

        return

    filename = (
        f"{student_id}.jpg"
    )

    filepath = os.path.join(
        KNOWN_FACES_FOLDER,
        filename
    )

    # --------------------------------------------------------
    # CHECK EXISTING STUDENT
    # --------------------------------------------------------

    if get_student(student_id):

        messagebox.showwarning(
            "Student Exists",
            "This Student ID is already registered."
        )

        return

    # --------------------------------------------------------
    # SAVE FACE
    # --------------------------------------------------------

    saved = cv2.imwrite(
        filepath,
        face_image
    )

    if not saved:

        messagebox.showerror(
            "Save Error",
            "Could not save face image."
        )

        return

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    added = add_student(
        student_id,
        name,
        department,
        email,
        filepath
    )

    if not added:

        try:
            os.remove(filepath)
        except:
            pass

        messagebox.showerror(
            "Database Error",
            "Student could not be registered."
        )

        return

    # --------------------------------------------------------
    # RELOAD FACES
    # --------------------------------------------------------

    load_known_faces()

    messagebox.showinfo(
        "Registration Successful",
        f"Student registered successfully!\n\n"
        f"Student ID: {student_id}\n"
        f"Name: {name}"
    )

    stop_camera()

    register_page()


# ============================================================
# REGISTERED STUDENTS PAGE
# ============================================================

def registered_students_page():

    clear_page()

    page_title(
        "Registered Students",
        "View all registered students"
    )

    frame = tk.Frame(
        page_container,
        bg=CARD
    )

    frame.pack(
        fill="both",
        expand=True
    )

    columns = (
        "id",
        "name",
        "department",
        "email"
    )

    table = create_treeview(
        frame,
        columns
    )

    table.heading(
        "id",
        text="Student ID"
    )

    table.heading(
        "name",
        text="Name"
    )

    table.heading(
        "department",
        text="Department"
    )

    table.heading(
        "email",
        text="Email"
    )

    table.column(
        "id",
        width=150
    )

    table.column(
        "name",
        width=200
    )

    table.column(
        "department",
        width=220
    )

    table.column(
        "email",
        width=280
    )

    students = get_all_students()

    for student in students:

        table.insert(
            "",
            "end",
            values=(
                student[0],
                student[1],
                student[2] or "N/A",
                student[3] or "N/A"
            )
        )


# ============================================================
# TREEVIEW
# ============================================================

def create_treeview(
    parent,
    columns
):

    style = ttk.Style()

    try:

        style.theme_use(
            "clam"
        )

    except:
        pass

    style.configure(
        "Dark.Treeview",
        background=CARD_2,
        foreground=WHITE,
        fieldbackground=CARD_2,
        rowheight=38,
        font=("Arial", 10)
    )

    style.configure(
        "Dark.Treeview.Heading",
        background=SIDEBAR_ACTIVE,
        foreground=WHITE,
        font=("Arial", 10, "bold")
    )

    style.map(
        "Dark.Treeview",
        background=[
            ("selected", BLUE)
        ],
        foreground=[
            ("selected", WHITE)
        ]
    )

    tree = ttk.Treeview(
        parent,
        columns=columns,
        show="headings",
        style="Dark.Treeview"
    )

    scrollbar = ttk.Scrollbar(
        parent,
        orient="vertical",
        command=tree.yview
    )

    tree.configure(
        yscrollcommand=scrollbar.set
    )

    tree.pack(
        side="left",
        fill="both",
        expand=True,
        padx=15,
        pady=15
    )

    scrollbar.pack(
        side="right",
        fill="y",
        pady=15
    )

    return tree


# ============================================================
# ATTENDANCE RECORDS PAGE
# ============================================================

def attendance_records_page():

    clear_page()

    page_title(
        "Attendance Records",
        "Complete attendance history"
    )

    frame = tk.Frame(
        page_container,
        bg=CARD
    )

    frame.pack(
        fill="both",
        expand=True
    )

    columns = (
        "student_id",
        "name",
        "department",
        "date",
        "time",
        "status",
        "confidence"
    )

    table = create_treeview(
        frame,
        columns
    )

    table.heading(
        "student_id",
        text="Student ID"
    )

    table.heading(
        "name",
        text="Name"
    )

    table.heading(
        "department",
        text="Department"
    )

    table.heading(
        "date",
        text="Date"
    )

    table.heading(
        "time",
        text="Time"
    )

    table.heading(
        "status",
        text="Status"
    )

    table.heading(
        "confidence",
        text="Confidence"
    )

    for column in columns:

        table.column(
            column,
            width=130,
            anchor="center"
        )

    records = get_attendance()

    for record in records:

        confidence = (
            f"{float(record[6]):.2f}"
            if record[6] is not None
            else "N/A"
        )

        table.insert(
            "",
            "end",
            values=(
                record[0],
                record[1] or "Unknown",
                record[2] or "N/A",
                record[3],
                record[4],
                record[5],
                confidence
            )
        )


# ============================================================
# DELETE STUDENT PAGE
# ============================================================

def delete_student_page():

    clear_page()

    page_title(
        "Delete Student",
        "Remove a student and their attendance records"
    )

    card = tk.Frame(
        page_container,
        bg=CARD
    )

    card.pack(
        fill="x",
        padx=100,
        pady=30
    )

    tk.Label(
        card,
        text="DELETE STUDENT",
        font=("Arial", 18, "bold"),
        bg=CARD,
        fg=WHITE
    ).pack(
        pady=(30, 15)
    )

    tk.Label(
        card,
        text="Enter Student ID",
        font=("Arial", 11),
        bg=CARD,
        fg=MUTED
    ).pack()

    entry = tk.Entry(
        card,
        font=("Arial", 14),
        bg="#0f172a",
        fg=WHITE,
        insertbackground=WHITE,
        relief="flat",
        width=30
    )

    entry.pack(
        pady=12,
        ipady=8
    )

    info_label = tk.Label(
        card,
        text="",
        font=("Arial", 11),
        bg=CARD,
        fg=MUTED
    )

    info_label.pack(
        pady=10
    )

    def search_student():

        student_id = entry.get().strip()

        if not student_id:

            info_label.config(
                text="Enter a Student ID.",
                fg=RED
            )

            return

        student = get_student(
            student_id
        )

        if student is None:

            info_label.config(
                text="Student not found.",
                fg=RED
            )

            return

        info_label.config(
            text=(
                f"Name: {student[1]}\n"
                f"Department: {student[2] or 'N/A'}\n\n"
                f"Click DELETE STUDENT to remove."
            ),
            fg=TEXT
        )

    def delete():

        student_id = entry.get().strip()

        if not student_id:

            return

        student = get_student(
            student_id
        )

        if student is None:

            messagebox.showwarning(
                "Not Found",
                "Student not found."
            )

            return

        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Delete student '{student[1]}'?\n\n"
            "This will also delete their attendance records."
        )

        if not confirm:

            return

        image_path = student[4]

        deleted = delete_student(
            student_id
        )

        if deleted:

            if image_path and os.path.exists(
                image_path
            ):

                try:
                    os.remove(image_path)
                except:
                    pass

            load_known_faces()

            messagebox.showinfo(
                "Deleted",
                "Student deleted successfully."
            )

            delete_student_page()

        else:

            messagebox.showerror(
                "Error",
                "Student could not be deleted."
            )

    buttons = tk.Frame(
        card,
        bg=CARD
    )

    buttons.pack(
        pady=25
    )

    create_small_button(
        buttons,
        "SEARCH",
        search_student,
        BLUE
    )

    create_small_button(
        buttons,
        "DELETE STUDENT",
        delete,
        RED
    )


# ============================================================
# SIDEBAR MENU
# ============================================================

add_sidebar_button(
    "▣   Dashboard",
    dashboard_page
)

add_sidebar_button(
    "▣   Mark Attendance",
    attendance_page
)

add_sidebar_button(
    "＋   Register Student",
    register_page
)

add_sidebar_button(
    "☷   Registered Students",
    registered_students_page
)

add_sidebar_button(
    "✓   Attendance Records",
    attendance_records_page
)

add_sidebar_button(
    "×   Delete Student",
    delete_student_page
)


# ============================================================
# SYSTEM STATUS
# ============================================================

status_frame = tk.Frame(
    sidebar,
    bg=SIDEBAR
)

status_frame.pack(
    side="bottom",
    fill="x",
    padx=15,
    pady=20
)

tk.Label(
    status_frame,
    text="● SYSTEM ONLINE",
    font=("Arial", 9, "bold"),
    bg=SIDEBAR,
    fg=GREEN
).pack(
    anchor="w"
)

tk.Label(
    status_frame,
    text="Smart Attendance v1.0",
    font=("Arial", 8),
    bg=SIDEBAR,
    fg=MUTED
).pack(
    anchor="w",
    pady=(3, 0)
)


# ============================================================
# CLOSE APPLICATION
# ============================================================

def close_application():

    stop_camera()

    window.destroy()


window.protocol(
    "WM_DELETE_WINDOW",
    close_application
)


# ============================================================
# START
# ============================================================

print()
print("==============================================")
print(" SMART ATTENDANCE SYSTEM")
print("==============================================")
print(
    f"Registered faces: {len(known_face_ids)}"
)
print("System ready.")
print()


dashboard_page()

window.mainloop()
